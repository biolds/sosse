# Copyright 2022-2024 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import re
import unicodedata

from datetime import datetime
from hashlib import md5
from time import sleep, mktime
from traceback import format_exc

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import connection, models
from django.template.loader import get_template
from django.utils.html import format_html
from django.utils.timezone import now
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from PIL import Image
import feedparser

from .browser import AuthElemFailed, SkipIndexing
from .html_cache import HTMLAsset
from .html_snapshot import HTMLSnapshot
from .url import url_beautify, validate_url
from .utils import reverse_no_escape

crawl_logger = logging.getLogger('crawler')

DetectorFactory.seed = 0


def remove_accent(s):
    # append an ascii version to match on non-accented letters
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


class RegConfigField(models.Field):
    def db_type(self, connection):
        return 'regconfig'


def extern_link_flags():
    opt = ''
    if settings.SOSSE_LINKS_NO_REFERRER:
        opt += ' rel="noreferrer"'
    if settings.SOSSE_LINKS_NEW_TAB:
        opt += ' target="_blank"'
    return format_html(opt)


class Document(models.Model):
    SCREENSHOT_PNG = 'png'
    SCREENSHOT_JPG = 'jpg'
    SCREENSHOT_FORMAT = (
        (SCREENSHOT_PNG, SCREENSHOT_PNG),
        (SCREENSHOT_JPG, SCREENSHOT_JPG)
    )

    # Document info
    url = models.TextField(unique=True, validators=[validate_url])

    normalized_url = models.TextField()
    title = models.TextField()
    normalized_title = models.TextField()
    content = models.TextField()
    normalized_content = models.TextField()
    content_hash = models.TextField(null=True, blank=True)
    vector = SearchVectorField(null=True, blank=True)
    lang_iso_639_1 = models.CharField(max_length=6, null=True, blank=True, verbose_name='Language')
    vector_lang = RegConfigField(default='simple')
    mimetype = models.CharField(max_length=64, null=True, blank=True)
    hidden = models.BooleanField(default=False, help_text='Hide this document from search results')

    favicon = models.ForeignKey('FavIcon', null=True, blank=True, on_delete=models.SET_NULL)
    robotstxt_rejected = models.BooleanField(default=False, verbose_name='Rejected by robots.txt')
    has_html_snapshot = models.BooleanField(default=False)

    # HTTP status
    redirect_url = models.TextField(null=True, blank=True)
    too_many_redirects = models.BooleanField(default=False)

    screenshot_count = models.PositiveIntegerField(default=0)
    screenshot_format = models.CharField(max_length=3, choices=SCREENSHOT_FORMAT)
    screenshot_size = models.CharField(max_length=16)

    has_thumbnail = models.BooleanField(default=False)

    # Crawling info
    crawl_first = models.DateTimeField(blank=True, null=True, verbose_name='Crawled first')
    crawl_last = models.DateTimeField(blank=True, null=True, verbose_name='Crawled last')
    crawl_next = models.DateTimeField(blank=True, null=True, verbose_name='Crawl next')
    crawl_dt = models.DurationField(blank=True, null=True, verbose_name='Crawl DT')
    crawl_recurse = models.PositiveIntegerField(default=0, verbose_name='Recursion remaining')
    error = models.TextField(blank=True, default='')
    error_hash = models.TextField(blank=True, default='')
    show_on_homepage = models.BooleanField(default=False, help_text='Display this document on the homepage')

    worker_no = models.PositiveIntegerField(blank=True, null=True)

    supported_langs = None

    class Meta:
        indexes = [GinIndex(fields=(('vector',)))]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_name = None

    def __str__(self):
        return self.url

    def get_absolute_url(self):
        if self.screenshot_count or self.redirect_url:
            return reverse_no_escape('screenshot', args=(self.url,))

        if self.has_html_snapshot:
            asset = HTMLAsset.objects.filter(url=self.url).first()
            if asset and os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
                return reverse_no_escape('html', args=(self.url,))

        return reverse_no_escape('www', args=(self.url,))

    def get_source_link(self):
        link = '🌍 <a href="{}"'
        link += extern_link_flags()
        link += '>Source page</a>'
        return format_html(link, self.url)

    def image_name(self):
        if not self._image_name:
            filename = md5(self.url.encode('utf-8')).hexdigest()
            base_dir = filename[:2]
            self._image_name = os.path.join(base_dir, filename)
        return self._image_name

    @classmethod
    def get_supported_langs(cls):
        if cls.supported_langs is not None:
            return cls.supported_langs

        with connection.cursor() as cursor:
            cursor.execute("SELECT cfgname FROM pg_catalog.pg_ts_config WHERE cfgname != 'simple'")
            row = cursor.fetchall()

        cls.supported_langs = [r[0] for r in row]
        return cls.supported_langs

    @classmethod
    def get_supported_lang_dict(cls):
        supported = cls.get_supported_langs()
        langs = {}
        for iso, lang in settings.SOSSE_LANGDETECT_TO_POSTGRES.items():
            if lang['name'] in supported:
                langs[iso] = lang
        return langs

    @classmethod
    def _get_lang(cls, text):
        try:
            lang_iso = detect(text)
        except LangDetectException:
            lang_iso = None

        lang_pg = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')
        if lang_pg not in cls.get_supported_langs():
            lang_pg = settings.SOSSE_FAIL_OVER_LANG

        return lang_iso, lang_pg

    def lang_flag(self, full=False):
        lang = self.lang_iso_639_1
        flag = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang, {}).get('flag')

        if full:
            lang = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang, {}).get('name', lang)
        if flag:
            lang = f'{flag} {lang}'

        return lang

    def _hash_content(self, content, crawl_policy):
        assert isinstance(content, str)
        from .models import CrawlPolicy
        if crawl_policy.hash_mode == CrawlPolicy.HASH_RAW:
            pass
        elif crawl_policy.hash_mode == CrawlPolicy.HASH_NO_NUMBERS:
            try:
                content = re.sub('[0-9]+', '0', content)
            except UnicodeDecodeError:
                pass
        else:
            raise Exception('HASH_MODE not supported')

        return settings.HASHING_ALGO(content.encode('utf-8')).hexdigest()

    def _index_log(self, s, stats, verbose):
        if not verbose:
            return
        n = now()
        print('%s %s' % (n - stats['prev'], s))
        stats['prev'] = n

    def _clear_base_content(self):
        from .models import Link
        self.redirect_url = None
        self.too_many_redirects = False
        self.content = ''
        self.normalized_content = ''
        self.title = ''
        self.normalized_title = ''
        self.robotstxt_rejected = False
        self.mimetype = ''
        Link.objects.filter(doc_from=self).delete()

    def _clear_dump_content(self):
        self.delete_html()
        self.delete_screenshot()
        self.delete_thumbnail()

    def _parse_xml(self, page, crawl_policy, stats, verbose):
        parsed = feedparser.parse(page.content)
        if len(getattr(parsed, 'entries', [])) == 0:
            return

        for entry in parsed['entries']:
            if entry.get('updated_parsed'):
                entry['updated_datetime'] = datetime.fromtimestamp(mktime(entry['updated_parsed']))

        if getattr(parsed.feed, 'title', None):
            page.title = parsed.feed.title
            self.title = parsed.feed.title

        self.mimetype = 'text/html'

        template = get_template('se/feed.html')
        context = {'feed': parsed}
        page.content = template.render(context).encode('utf-8')
        page.soup = None
        page.mimetype = 'text/html'
        crawl_logger.debug('%s is a rss/atom feed with %s items', self.url, len(parsed['entries']))

    def _parse_text(self, page, crawl_policy, stats, verbose):
        crawl_logger.debug('parsing %s', self.url)
        links = page.dom_walk(crawl_policy, True, self)
        text = links['text']

        self._index_log('text / %i links extraction' % len(links['links']), stats, verbose)

        self.content = text
        self.normalized_content = remove_accent(text)
        self.lang_iso_639_1, self.vector_lang = self._get_lang((page.title or '') + '\n' + text)
        self._index_log('remove accent', stats, verbose)

        # The bulk request triggers a deadlock
        # Link.objects.bulk_create(links['links'])
        for link in links['links']:
            link.save()
        self._index_log('bulk', stats, verbose)
        return links

    def index(self, page, crawl_policy, verbose=False, force=False):
        n = now()
        stats = {'prev': n}
        self._index_log('start', stats, verbose)

        self._clear_base_content()
        self._index_log('queuing links', stats, verbose)

        beautified_url = url_beautify(page.url)
        normalized_url = beautified_url.split('://', 1)[1].replace('/', ' ').strip()
        self.normalized_url = remove_accent(normalized_url)
        if page.title:
            self.title = page.title
        else:
            self.title = beautified_url

        self.normalized_title = remove_accent(self.title)
        self.hidden = crawl_policy.hide_documents

        # dirty hack to avoid some errors (as triggered since bookworm during tests)
        magic_head = page.content[:20].strip().lower()
        is_html = False
        for header in ('<html', '<!doctype html'):
            is_html |= isinstance(magic_head, str) and magic_head.startswith(header)
            is_html |= isinstance(magic_head, bytes) and magic_head.startswith(header.encode('utf-8'))

        if is_html:
            self.mimetype = 'text/html'
        else:
            from magic import from_buffer as magic_from_buffer
            self.mimetype = magic_from_buffer(page.content, mime=True)

        self.crawl_last = n
        if not self.crawl_first:
            self.crawl_first = n

        if not re.match(crawl_policy.mimetype_regex, self.mimetype):
            self._schedule_next(False, crawl_policy)

            crawl_logger.debug('skipping %s due to mimetype %s' % (self.url, self.mimetype))
            return

        self._parse_xml(page, crawl_policy, stats, verbose)
        if self.mimetype.startswith('text/'):
            links = self._parse_text(page, crawl_policy, stats, verbose)

        content_hash = self._hash_content(self.content, crawl_policy)
        self._schedule_next(self.content_hash != content_hash, crawl_policy)

        if self.content_hash == content_hash and not force:
            return
        self.content_hash = content_hash

        self._clear_dump_content()

        if self.mimetype.startswith('text/'):
            if crawl_policy.create_thumbnails:
                crawl_policy.get_browser(url=self.url).create_thumbnail(self.url, self.image_name())
                self.has_thumbnail = True

        if self.mimetype.startswith('text/'):
            from .models import FavIcon
            FavIcon.extract(self, page)
            self._index_log('favicon', stats, verbose)

        if crawl_policy.snapshot_html:
            from .models import CrawlPolicy
            if crawl_policy.remove_nav_elements == CrawlPolicy.REMOVE_NAV_FROM_ALL:
                page.remove_nav_elements()
            snapshot = HTMLSnapshot(page, crawl_policy)
            snapshot.snapshot()
            self.has_html_snapshot = True

        if self.mimetype.startswith('text/'):
            if crawl_policy.take_screenshots:
                self.screenshot_index(links['links'], crawl_policy)

        self._index_log('done', stats, verbose)

    def convert_to_jpg(self):
        d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, self.image_name())

        for i in range(self.screenshot_count):
            src = '%s_%s.png' % (d, i)
            dst = '%s_%s.jpg' % (d, i)
            crawl_logger.debug('Converting %s to %s' % (src, dst))

            img = Image.open(src)
            img = img.convert('RGB')  # Remove alpha channel from the png
            img.save(dst, 'jpeg')
            os.unlink(src)

    def screenshot_index(self, links, crawl_policy):
        from .models import CrawlPolicy
        if crawl_policy.remove_nav_elements in (CrawlPolicy.REMOVE_NAV_FROM_ALL, CrawlPolicy.REMOVE_NAV_FROM_SCREENSHOT):
            browser = crawl_policy.get_browser(url=self.url)
            browser.remove_nav_elements()

        browser = crawl_policy.get_browser(url=self.url)
        img_count = browser.take_screenshots(self.url, self.image_name())
        crawl_logger.debug('took %s screenshots for %s with %s', img_count, self.url, browser)
        self.screenshot_count = img_count
        self.screenshot_format = crawl_policy.screenshot_format
        self.screenshot_size = '%sx%s' % browser.screen_size()

        if crawl_policy.screenshot_format == Document.SCREENSHOT_JPG:
            self.convert_to_jpg()

        browser.scroll_to_page(0)
        for i, link in enumerate(links):
            loc = browser.get_link_pos_abs(link.css_selector)
            if loc == {}:
                continue
            for attr in ('elemLeft', 'elemTop', 'elemRight', 'elemBottom'):
                if not isinstance(loc[attr], (int, float)):
                    break
            else:
                link.screen_pos = '%s,%s,%s,%s' % (
                    int(loc['elemLeft']),
                    int(loc['elemTop']),
                    int(loc['elemRight'] - loc['elemLeft']),
                    int(loc['elemBottom'] - loc['elemTop'])
                )
                link.save()

    def set_error(self, err):
        self.error = err
        if err == '':
            self.error_hash = ''
        else:
            self.error_hash = md5(err.encode('utf-8')).hexdigest()

    @staticmethod
    def queue(url, parent_policy, parent):
        from .models import CrawlPolicy, ExcludedUrl
        if ExcludedUrl.objects.filter(url=url, starting_with=False).first():
            crawl_logger.debug('skipping ExcludedUrl %s', url)
            return None

        if ExcludedUrl.objects.filter(starting_with=True).extra(where=['starts_with(%s, url)'], params=[url]).first():
            crawl_logger.debug('skipping ExcludedUrl %s', url)
            return None

        crawl_policy = CrawlPolicy.get_from_url(url)
        crawl_logger.debug('%s matched %s, %s' % (url, crawl_policy.url_regex, crawl_policy.recursion))

        if crawl_policy.recursion == CrawlPolicy.CRAWL_ALL or parent is None:
            crawl_logger.debug('%s -> always crawl' % url)
            return Document.objects.get_or_create(url=url, hidden=crawl_policy.hide_documents)[0]

        if crawl_policy.recursion == CrawlPolicy.CRAWL_NEVER:
            crawl_logger.debug('%s -> never crawl' % url)
            return Document.objects.filter(url=url).first()

        doc = None
        url_depth = None

        if parent_policy.recursion == CrawlPolicy.CRAWL_ALL and parent_policy.recursion_depth > 0:
            doc = Document.objects.get_or_create(url=url, hidden=crawl_policy.hide_documents)[0]
            url_depth = max(parent_policy.recursion_depth, doc.crawl_recurse)
            crawl_logger.debug('%s -> recurse for %s' % (url, url_depth))
        elif parent_policy.recursion == CrawlPolicy.CRAWL_ON_DEPTH and parent.crawl_recurse > 1:
            doc = Document.objects.get_or_create(url=url, hidden=crawl_policy.hide_documents)[0]
            url_depth = max(parent.crawl_recurse - 1, doc.crawl_recurse)
            crawl_logger.debug('%s -> recurse at %s' % (url, url_depth))
        else:
            crawl_logger.debug('%s -> no recurse (from parent %s)' % (url, parent_policy.recursion))

        if doc and url_depth != doc.crawl_recurse:
            doc.crawl_recurse = url_depth
            doc.save()

        doc = doc or Document.objects.filter(url=url).first()
        return doc

    def _schedule_next(self, changed, crawl_policy):
        from .models import CrawlPolicy
        stop = False
        if crawl_policy.recursion == CrawlPolicy.CRAWL_NEVER or \
                (crawl_policy.recursion == CrawlPolicy.CRAWL_ON_DEPTH and self.crawl_recurse == 0):
            stop = True

        if crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_NONE or stop:
            self.crawl_next = None
            self.crawl_dt = None
        elif crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_CONSTANT:
            self.crawl_next = self.crawl_last + crawl_policy.recrawl_dt_min
            self.crawl_dt = None
        elif crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_ADAPTIVE:
            if self.crawl_dt is None:
                self.crawl_dt = crawl_policy.recrawl_dt_min
            elif not changed:
                self.crawl_dt = min(crawl_policy.recrawl_dt_max, self.crawl_dt * 2)
            else:
                self.crawl_dt = max(crawl_policy.recrawl_dt_min, self.crawl_dt / 2)
            self.crawl_next = self.crawl_last + self.crawl_dt

    @staticmethod
    def crawl(worker_no):
        from .models import CrawlPolicy, DomainSetting, Link, WorkerStats
        doc = Document.pick_queued(worker_no)
        if doc is None:
            return False

        worker_stats = WorkerStats.get_worker(worker_no)
        if worker_stats.state != 'running':
            worker_stats.update_state('running')

        crawl_logger.debug('Worker:%i Queued:%i Indexed:%i Id:%i %s ...' % (worker_no,
                           Document.objects.filter(crawl_last__isnull=True).count(),
                           Document.objects.filter(crawl_last__isnull=False).count(),
                           doc.id, doc.url))

        while True:
            # Loop until we stop redirecting
            crawl_policy = CrawlPolicy.get_from_url(doc.url)
            crawl_logger.debug('Crawling %s with policy %s', doc.url, crawl_policy)
            try:
                WorkerStats.objects.filter(id=worker_stats.id).update(doc_processed=models.F('doc_processed') + 1)
                doc.worker_no = None
                doc.crawl_last = now()

                if doc.url.startswith('http://') or doc.url.startswith('https://'):
                    domain_setting = DomainSetting.get_from_url(doc.url, crawl_policy.default_browse_mode)

                    if not domain_setting.robots_authorized(doc.url):
                        crawl_logger.debug('%s rejected by robots.txt' % doc.url)
                        doc.robotstxt_rejected = True
                        n = now()
                        doc.crawl_last = n
                        if not doc.crawl_first:
                            doc.crawl_first = n
                        doc.crawl_next = None
                        doc.crawl_dt = None
                        doc.save()
                        break
                    else:
                        doc.robotstxt_rejected = False

                    try:
                        page = crawl_policy.url_get(doc.url, domain_setting)
                    except AuthElemFailed as e:
                        doc.content = e.page.content.decode('utf-8')
                        doc._schedule_next(True, crawl_policy)
                        doc.set_error(f'Locating authentication element failed at {e.page.url}:\n{e.args[0]}')
                        doc.save()
                        crawl_logger.error(f'Locating authentication element failed at {e.page.url}:\n{e.args[0]}')
                        break
                    except SkipIndexing as e:
                        doc._schedule_next(False, crawl_policy)
                        doc.set_error(e.args[0])
                        doc.save()
                        crawl_logger.debug(f'{doc.url}: {e.args[0]}')
                        break

                    if page.url == doc.url:
                        doc.index(page, crawl_policy)
                        doc.set_error('')
                        doc.save()
                        Link.objects.filter(extern_url=doc.url).update(extern_url=None, doc_to=doc)
                        break
                    else:
                        if not page.redirect_count:
                            raise Exception('redirect not set %s -> %s' % (doc.url, page.url))
                        crawl_logger.debug('%i redirect %s -> %s (redirect no %i)' % (worker_no, doc.url, page.url, page.redirect_count))
                        doc._schedule_next(doc.redirect_url != page.url, crawl_policy)
                        doc._clear_base_content()
                        doc._clear_dump_content()
                        doc.set_error('')
                        doc.redirect_url = page.url
                        doc.save()

                        # Process the page if it's new, otherwise skip it since it'll be processed depending on `crawl_next`
                        if Document.objects.filter(url=page.url).count():
                            break

                        doc = Document.pick_or_create(page.url, worker_no)
                        if doc is None:
                            break
                else:
                    break
            except Exception as e:  # noqa
                doc.set_error(format_exc())
                doc._schedule_next(True, crawl_policy)
                doc.save()
                crawl_logger.error(format_exc())
                if getattr(settings, 'TEST_MODE', False):
                    raise
                break

            worker_stats.refresh_from_db()
            if worker_stats.state == 'paused':
                doc.worker_no = None
                doc.save()
                break

        return True

    @staticmethod
    def pick_queued(worker_no):
        while True:
            doc = Document.objects.filter(worker_no__isnull=True,
                                          crawl_last__isnull=True).order_by('id').first()
            if doc is None:
                doc = Document.objects.filter(worker_no__isnull=True,
                                              crawl_last__isnull=False,
                                              crawl_next__lte=now()).order_by('crawl_next', 'id').first()
                if doc is None:
                    return None

            updated = Document.objects.filter(id=doc.id,
                                              worker_no__isnull=True).update(worker_no=worker_no)

            if updated == 0:
                sleep(0.1)
                continue

            try:
                doc.refresh_from_db()
            except Document.DoesNotExist:
                sleep(0.1)
                continue

            return doc

    @staticmethod
    def pick_or_create(url, worker_no):
        doc, created = Document.objects.get_or_create(url=url,
                                                      defaults={'worker_no': worker_no})
        if created:
            return doc

        updated = Document.objects.filter(id=doc.id,
                                          worker_no__isnull=True).update(worker_no=worker_no)

        if updated == 0:
            return None

        try:
            doc.refresh_from_db()
        except Document.DoesNotExist:
            pass

        return doc

    def delete_html(self):
        if self.has_html_snapshot:
            HTMLAsset.html_delete_url(self.url)
            self.has_html_snapshot = False

    def delete_screenshot(self):
        if self.screenshot_count:
            d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, self.image_name())

            for i in range(self.screenshot_count):
                filename = '%s_%s.%s' % (d, i, self.screenshot_format)
                if os.path.exists(filename):
                    os.unlink(filename)
            self.screenshot_count = 0

    def delete_thumbnail(self):
        if self.has_thumbnail:
            f = os.path.join(settings.SOSSE_THUMBNAILS_DIR, self.image_name()) + '.jpg'
            if os.path.exists(f):
                os.unlink(f)
            self.has_thumbnail = False

    def delete_all(self):
        self.delete_html()
        self.delete_screenshot()
        self.delete_thumbnail()

    def default_domain_setting(self):
        from se.models import DomainSetting
        return DomainSetting.get_from_url(self.url)
