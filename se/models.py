# Copyright 2022-2023 Laurent Defert
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

import os
import re
import urllib.parse
import unicodedata
import logging

from base64 import b64encode, b64decode
from datetime import timedelta
from defusedxml import ElementTree
from hashlib import md5
from time import sleep
from traceback import format_exc
from urllib.parse import quote, quote_plus, unquote, unquote_plus, urlparse

from bs4 import Doctype, Tag
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import connection, models
from django.http import QueryDict
from django.utils.timezone import now
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from PIL import Image
from publicsuffix2 import get_public_suffix, PublicSuffixList
import requests

from .browser import AuthElemFailed, RequestBrowser, SeleniumBrowser, SkipIndexing
from .utils import reverse_no_escape, url_beautify

DetectorFactory.seed = 0

crawl_logger = logging.getLogger('crawler')


def sanitize_url(url, keep_params, keep_anchors):
    if not keep_params:
        if '?' in url:
            url = url.split('?', 1)[0]

    if not keep_anchors:
        if '#' in url:
            url = url.split('#', 1)[0]

    url = urlparse(url)

    # normalize percent-encoding
    _path = unquote(url.path)
    url = url._replace(path=quote(_path))

    _query = unquote_plus(url.query)
    url = url._replace(query=quote_plus(_query, safe='&='))

    # normalize punycode
    try:
        url.netloc.encode('ascii')
    except UnicodeEncodeError:
        try:
            url = url._replace(netloc=url.netloc.encode('idna').decode())
        except:  # noqa: E722
            pass

    if url.path == '':
        url = url._replace(path='/')
    else:
        new_path = os.path.abspath(url.path)
        new_path = new_path.replace('//', '/')
        if url.path.endswith('/') and url.path != '/':
            # restore traling / (deleted by abspath)
            new_path += '/'
        url = url._replace(path=new_path)

    url = url.geturl()
    return url


def absolutize_url(url, p, keep_params, keep_anchors):
    if p.startswith('data:'):
        return p

    if p == '':
        return sanitize_url(url, keep_params, keep_anchors)

    if p.startswith('//'):
        scheme = url.split('//', 1)[0]
        p = scheme + p

    if re.match('[a-zA-Z]+:', p):
        return sanitize_url(p, keep_params, keep_anchors)

    url = urlparse(url)

    if p.startswith('./'):
        p = p[2:]

    if p.startswith('/'):
        new_path = p
    else:
        new_path = os.path.dirname(url.path)
        if not new_path.endswith('/'):
            new_path += '/'

        new_path += p

    # clear params: new params are already contained in new_path
    url = url._replace(path=new_path, query='')
    return sanitize_url(url.geturl(), keep_params, keep_anchors)


def remove_accent(s):
    # append an ascii version to match on non-accented letters
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


class RegConfigField(models.Field):
    def db_type(self, connection):
        return 'regconfig'


def validate_url(url):
    URL_REGEXP = r'https?://[a-zA-Z0-9_-][a-zA-Z0-9\_\-\.]*(:[0-9]+)?/[a-zA-Z0-9\_\.\-\~\/\?\&\=\%\+]*$'
    if not re.match(URL_REGEXP, url):
        raise ValidationError('URL must match the regular expression: %s' % URL_REGEXP)


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

    favicon = models.ForeignKey('FavIcon', null=True, blank=True, on_delete=models.SET_NULL)
    robotstxt_rejected = models.BooleanField(default=False, verbose_name='Rejected by robots.txt')

    # HTTP status
    redirect_url = models.TextField(null=True, blank=True)
    too_many_redirects = models.BooleanField(default=False)

    screenshot_file = models.CharField(max_length=4096, blank=True, null=True)
    screenshot_count = models.PositiveIntegerField(blank=True, null=True)
    screenshot_format = models.CharField(max_length=3, choices=SCREENSHOT_FORMAT)
    screenshot_size = models.CharField(max_length=16)

    # Crawling info
    crawl_first = models.DateTimeField(blank=True, null=True, verbose_name='Crawled first')
    crawl_last = models.DateTimeField(blank=True, null=True, verbose_name='Crawled last')
    crawl_next = models.DateTimeField(blank=True, null=True, verbose_name='Crawl next')
    crawl_dt = models.DurationField(blank=True, null=True, verbose_name='Crawl DT')
    crawl_recurse = models.PositiveIntegerField(default=0, verbose_name='Recursion remaining')
    error = models.TextField(blank=True, default='')
    error_hash = models.TextField(blank=True, default='')
    worker_no = models.PositiveIntegerField(blank=True, null=True)

    supported_langs = None

    class Meta:
        indexes = [GinIndex(fields=(('vector',)))]

    def __str__(self):
        return self.url

    def get_absolute_url(self):
        if self.screenshot_file:
            return reverse_no_escape('screenshot', args=(self.url,))
        else:
            return reverse_no_escape('www', args=(self.url,))

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
        if crawl_policy.hash_mode == CrawlPolicy.HASH_RAW:
            pass
        elif crawl_policy.hash_mode == CrawlPolicy.HASH_NO_NUMBERS:
            if isinstance(content, str):
                content = re.sub('[0-9]+', '0', content)
        else:
            raise Exception('HASH_MODE not supported')

        if isinstance(content, bytes):
            return settings.HASHING_ALGO(content).hexdigest()
        return settings.HASHING_ALGO(content.encode('utf-8')).hexdigest()

    def _index_log(self, s, stats, verbose):
        if not verbose:
            return
        n = now()
        print('%s %s' % (n - stats['prev'], s))
        stats['prev'] = n

    def _build_selector(self, elem):
        no = 1
        for sibling in elem.previous_siblings:
            if isinstance(elem, Tag) and sibling.name == elem.name:
                no += 1

        selector = '/%s[%i]' % (elem.name, no)

        if elem.name != 'html':
            selector = self._build_selector(elem.parent) + selector
        return selector

    def _get_elem_text(self, elem, recurse=False):
        s = ''
        if elem.name is None:
            s = getattr(elem, 'string', '') or ''
            s = s.strip(' \t\n\r')

        if (elem.name == 'a' or recurse) and hasattr(elem, 'children'):
            for child in elem.children:
                _s = self._get_elem_text(child, True)
                if _s:
                    if s:
                        s += ' '
                    s += _s
        return s

    def _dom_walk(self, elem, crawl_policy, links):
        if isinstance(elem, Doctype):
            return

        if elem.name in ('[document]', 'title', 'script', 'style'):
            return

        s = self._get_elem_text(elem)

        # Keep the link if it has text, or if we take screenshots
        if elem.name in (None, 'a') and (s or crawl_policy.take_screenshots):
            if links['text'] and links['text'][-1] not in (' ', '\n'):
                links['text'] += ' '

            if elem.name == 'a':
                href = elem.get('href')
                if href and not href.startswith('data:'):
                    href = href.strip()

                    href_for_policy = absolutize_url(self.url, href, True, True)
                    child_policy = CrawlPolicy.get_from_url(href_for_policy)
                    href = absolutize_url(self.url, href, child_policy.keep_params, False)
                    target = Document.queue(href, crawl_policy, self)

                    if target != self:
                        link = None
                        if target:
                            link = Link(doc_from=self,
                                        link_no=len(links['links']),
                                        doc_to=target,
                                        text=s,
                                        pos=len(links['text']))
                        elif crawl_policy.store_extern_links:
                            href = elem.get('href').strip()
                            href = absolutize_url(self.url, href, True, True)
                            link = Link(doc_from=self,
                                        link_no=len(links['links']),
                                        text=s,
                                        pos=len(links['text']),
                                        extern_url=href)

                        if link:
                            if crawl_policy.take_screenshots:
                                link.css_selector = self._build_selector(elem)
                            links['links'].append(link)

            if s:
                links['text'] += s

            if elem.name == 'a':
                return

        if hasattr(elem, 'children'):
            for child in elem.children:
                self._dom_walk(child, crawl_policy, links)

        if elem.name in ('div', 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            if links['text']:
                if links['text'][-1] == ' ':
                    links['text'] = links['text'][:-1] + '\n'
                elif links['text'][-1] != '\n':
                    links['text'] += '\n'

    def _clear_content(self):
        self.redirect_url = None
        self.too_many_redirects = False
        self.content = ''
        self.normalized_content = ''
        self.title = ''
        self.normalized_title = ''
        self.delete_screenshot()
        Link.objects.filter(doc_from=self).delete()

    def index(self, page, crawl_policy, verbose=False, force=False):
        n = now()
        stats = {'prev': n}
        content_hash = self._hash_content(page.content, crawl_policy)
        self._index_log('hash', stats, verbose)

        self.crawl_last = n
        if not self.crawl_first:
            self.crawl_first = n
        self._schedule_next(self.content_hash != content_hash, crawl_policy)
        if self.content_hash == content_hash and not force:
            return

        self.content_hash = content_hash
        self._index_log('queuing links', stats, verbose)

        beautified_url = url_beautify(page.url)
        normalized_url = beautified_url.split('://', 1)[1].replace('/', ' ').strip()
        self.normalized_url = remove_accent(normalized_url)
        from magic import from_buffer as magic_from_buffer
        self.mimetype = magic_from_buffer(page.content, mime=True)

        if not re.match(crawl_policy.mimetype_regex, self.mimetype):
            crawl_logger.debug('skipping %s due to mimetype %s' % (self.url, self.mimetype))
            return

        if self.mimetype.startswith('text/'):
            parsed = page.get_soup()
            if page.title:
                self.title = page.title
            else:
                self.title = beautified_url

            self.normalized_title = remove_accent(self.title)

            self._index_log('get soup', stats, verbose)

            links = {
                'links': [],
                'text': ''
            }
            for elem in parsed.children:
                self._dom_walk(elem, crawl_policy, links)
            text = links['text']

            self._index_log('text / %i links extraction' % len(links['links']), stats, verbose)

            self.content = text
            self.normalized_content = remove_accent(text)
            self.lang_iso_639_1, self.vector_lang = self._get_lang((page.title or '') + '\n' + text)
            self._index_log('remove accent', stats, verbose)

            Link.objects.filter(doc_from=self).delete()
            self._index_log('delete', stats, verbose)

            # The bulk request triggers a deadlock
            # Link.objects.bulk_create(links['links'])
            for link in links['links']:
                link.save()
            self._index_log('bulk', stats, verbose)

            if crawl_policy.take_screenshots:
                self.screenshot_index(links['links'], crawl_policy)
        else:
            self._clear_content()

        FavIcon.extract(self, page)
        self._index_log('favicon', stats, verbose)

    def convert_to_jpg(self):
        d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, self.screenshot_file)

        for i in range(self.screenshot_count):
            src = '%s_%s.png' % (d, i)
            dst = '%s_%s.jpg' % (d, i)
            crawl_logger.debug('Converting %s to %s' % (src, dst))

            img = Image.open(src)
            img = img.convert('RGB')  # Remove alpha channel from the png
            img.save(dst, 'jpeg')
            os.unlink(src)

    def screenshot_index(self, links, crawl_policy):
        filename, img_count = SeleniumBrowser.take_screenshots(self.url)

        self.screenshot_file = filename
        self.screenshot_count = img_count
        self.screenshot_format = crawl_policy.screenshot_format
        self.screenshot_size = '%sx%s' % SeleniumBrowser.screen_size()

        if crawl_policy.screenshot_format == Document.SCREENSHOT_JPG:
            self.convert_to_jpg()

        SeleniumBrowser.scroll_to_page(0)
        for i, link in enumerate(links):
            loc = SeleniumBrowser.get_link_pos_abs(link.css_selector)
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
        if ExcludedUrl.objects.filter(url=url).first():
            return None

        crawl_policy = CrawlPolicy.get_from_url(url)
        crawl_logger.debug('%s matched %s, %s' % (url, crawl_policy.url_regex, crawl_policy.condition))

        if crawl_policy.condition == CrawlPolicy.CRAWL_ALL or parent is None:
            crawl_logger.debug('%s -> always crawl' % url)
            return Document.objects.get_or_create(url=url)[0]

        if crawl_policy.condition == CrawlPolicy.CRAWL_NEVER:
            crawl_logger.debug('%s -> never crawl' % url)
            return Document.objects.filter(url=url).first()

        doc = None
        url_depth = None

        if parent_policy.condition == CrawlPolicy.CRAWL_ALL and parent_policy.crawl_depth > 0:
            doc = Document.objects.get_or_create(url=url)[0]
            url_depth = max(parent_policy.crawl_depth, doc.crawl_recurse)
            crawl_logger.debug('%s -> recurse for %s' % (url, url_depth))
        elif parent_policy.condition == CrawlPolicy.CRAWL_ON_DEPTH and parent.crawl_recurse > 1:
            doc = Document.objects.get_or_create(url=url)[0]
            url_depth = max(parent.crawl_recurse - 1, doc.crawl_recurse)
            crawl_logger.debug('%s -> recurse at %s' % (url, url_depth))
        else:
            crawl_logger.debug('%s -> no recurse (from parent %s)' % (url, parent_policy.condition))

        if doc and url_depth != doc.crawl_recurse:
            doc.crawl_recurse = url_depth
            doc.save()

        doc = doc or Document.objects.filter(url=url).first()
        return doc

    def _schedule_next(self, changed, crawl_policy):
        stop = False
        if crawl_policy.condition == CrawlPolicy.CRAWL_NEVER or \
                (crawl_policy.condition == CrawlPolicy.CRAWL_ON_DEPTH and self.crawl_recurse == 0):
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
                        break
                    else:
                        doc.robotstxt_rejected = False

                    try:
                        page = crawl_policy.url_get(domain_setting, doc.url)
                    except AuthElemFailed as e:
                        doc.content = e.page.content
                        doc._schedule_next(True, crawl_policy)
                        doc.set_error(f'Locating authentication element failed at {e.page.url}:\n{e.args[0]}')
                        crawl_logger.error(f'Locating authentication element failed at {e.page.url}:\n{e.args[0]}')
                        break
                    except SkipIndexing as e:
                        doc._schedule_next(False, crawl_policy)
                        doc.set_error(e.args[0])
                        crawl_logger.debug(f'{doc.url}: {e.args[0]}')
                        break

                    if page.url == doc.url:
                        doc.index(page, crawl_policy)
                        doc.set_error('')
                        break
                    else:
                        if not page.redirect_count:
                            raise Exception('redirect not set %s -> %s' % (doc.url, page.url))
                        crawl_logger.debug('%i redirect %s -> %s (redirect no %i)' % (worker_no, doc.url, page.url, page.redirect_count))
                        doc._schedule_next(doc.url != page.url, crawl_policy)
                        doc._clear_content()
                        doc.redirect_url = page.url
                        doc.save()
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
                break

            worker_stats.refresh_from_db()
            if worker_stats.state == 'paused':
                doc.worker_no = None
                break

        if doc:
            doc.save()

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

    def delete_screenshot(self):
        if self.screenshot_file:
            d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, self.screenshot_file)

            for i in range(self.screenshot_count):
                filename = '%s_%s.%s' % (d, i, self.screenshot_format)
                if os.path.exists(filename):
                    os.unlink(filename)


class Link(models.Model):
    doc_from = models.ForeignKey(Document, null=True, blank=True, on_delete=models.SET_NULL, related_name='links_to')
    doc_to = models.ForeignKey(Document, null=True, blank=True, on_delete=models.CASCADE, related_name='linked_from')
    text = models.TextField(null=True, blank=True)
    pos = models.PositiveIntegerField()
    link_no = models.PositiveIntegerField()
    extern_url = models.TextField(null=True, blank=True)
    screen_pos = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        unique_together = ('doc_from', 'link_no')

    def pos_left(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(',')[0]

    def pos_top(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(',')[1]

    def pos_bottom(self):
        if not self.screen_pos:
            return 0
        return str(100 - int(self.screen_pos.split(',')[1]))

    def pos_width(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(',')[2]

    def pos_height(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(',')[3]


class AuthField(models.Model):
    key = models.CharField(max_length=256, verbose_name='<input> name attribute')
    value = models.CharField(max_length=256)
    crawl_policy = models.ForeignKey('CrawlPolicy', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'authentication field'


MINUTELY = 'M'
DAILY = 'D'
FREQUENCY = (
    (MINUTELY, MINUTELY),
    (DAILY, DAILY),
)


class WorkerStats(models.Model):
    STATE = (
        ('idle', 'Idle'),
        ('running', 'Running'),
        ('paused', 'Paused'),
    )

    doc_processed = models.PositiveIntegerField(default=0)
    worker_no = models.IntegerField()
    pid = models.PositiveIntegerField()
    state = models.CharField(max_length=8, choices=STATE, default='idle')

    @classmethod
    def get_worker(cls, worker_no):
        return cls.objects.update_or_create(worker_no=worker_no, defaults={'pid': os.getpid()})[0]

    def update_state(self, state):
        WorkerStats.objects.filter(worker_no=self.worker_no).exclude(state='paused').update(state=state)

    @classmethod
    def live_state(cls):
        workers = cls.objects.order_by('worker_no')
        for w in workers:
            args = []
            if os.path.exists('/proc/%s/cmdline' % w.pid):
                with open('/proc/%s/cmdline' % w.pid, 'br') as fd:
                    args = fd.read().split(b'\0')

            for i, arg in enumerate(args):
                if i == len(args) - 1:
                    continue
                if arg.endswith(b'sosse-admin') and args[i + 1] == b'crawl':
                    break
            else:
                w.pid = '-'
                w.state = 'exited'
        return workers


class CrawlerStats(models.Model):
    t = models.DateTimeField()
    doc_count = models.PositiveIntegerField()
    queued_url = models.PositiveIntegerField()
    indexing_speed = models.PositiveIntegerField(blank=True, null=True)
    freq = models.CharField(max_length=1, choices=FREQUENCY)

    @staticmethod
    def create(t):
        CrawlerStats.objects.filter(t__lt=t - timedelta(hours=24), freq=MINUTELY).delete()
        CrawlerStats.objects.filter(t__lt=t - timedelta(days=365), freq=DAILY).delete()

        doc_processed = WorkerStats.objects.filter().aggregate(s=models.Sum('doc_processed')).get('s', 0) or 0
        WorkerStats.objects.update(doc_processed=0)

        doc_count = Document.objects.count()
        queued_url = Document.objects.filter(crawl_last__isnull=True).count() + Document.objects.filter(crawl_next__lte=now()).count()

        today = now().replace(hour=0, minute=0, second=0, microsecond=0)
        entry, _ = CrawlerStats.objects.get_or_create(t=today, freq=DAILY, defaults={'doc_count': 0, 'queued_url': 0, 'indexing_speed': 0})
        entry.indexing_speed += doc_processed
        entry.doc_count = doc_count
        entry.queued_url = max(queued_url, entry.queued_url)
        entry.save()

        CrawlerStats.objects.create(t=t,
                                    doc_count=doc_count,
                                    queued_url=queued_url,
                                    indexing_speed=doc_processed,
                                    freq=MINUTELY)


def validate_search_url(value):
    if '{searchTerms}' not in value and '{searchTermsBase64}' not in value:
        raise ValidationError('This field must contain the search url with a {searchTerms} or a {searchTermsBase64} string parameter')


class SearchEngine(models.Model):
    short_name = models.CharField(max_length=32, blank=True, default='')
    long_name = models.CharField(max_length=48, blank=True, default='')
    description = models.CharField(max_length=1024, blank=True, default='')
    html_template = models.CharField(max_length=2048, validators=[validate_search_url])
    shortcut = models.CharField(max_length=16, blank=True)

    def __str__(self):
        return self.short_name

    @classmethod
    def parse_odf(cls, content):
        root = ElementTree.fromstring(content)
        ns = root.tag[:-len('OpenSearchDescription')]

        short_name_elem = root.find(ns + 'ShortName')
        if short_name_elem is None:
            print('No ShortName defined')
            return

        short_name = short_name_elem.text
        se = None
        try:
            se = cls.objects.get(short_name=short_name)
        except SearchEngine.DoesNotExist:
            se = SearchEngine(short_name=short_name)

        long_name = root.find(ns + 'LongName')
        if long_name is None:
            long_name = short_name
        else:
            long_name = long_name.text
        se.long_name = long_name
        se.description = root.find(ns + 'Description').text

        for elem in root.findall(ns + 'Url'):
            if elem.get('type') == 'text/html':
                se.html_template = elem.get('template')
            elif elem.get('type') == 'application/x-suggestions+json':
                se.suggestion_template = elem.get('template')

        se.shortcut = short_name.lower().split(' ')[0]
        se.save()

    @classmethod
    def parse_xml_file(cls, f):
        with open(f, 'r') as fd:
            buf = fd.read()

        cls.parse_odf(buf)

    def get_search_url(self, query):
        se_url = urllib.parse.urlsplit(self.html_template)

        # In url path
        if '{searchTerms}' in se_url.path:
            query = urllib.parse.quote_plus(query)
            se_url_path = se_url.path.replace('{searchTerms}', query)
            se_url = se_url._replace(path=se_url_path)
            return urllib.parse.urlunsplit(se_url)

        if '{searchTermsBase64}' in se_url.path:
            query = urllib.parse.quote_plus(b64encode(query.encode('utf-8')).decode('utf-8'))
            se_url_path = se_url.path.replace('{searchTermsBase64}', query)
            se_url = se_url._replace(path=se_url_path)
            return urllib.parse.urlunsplit(se_url)

        # In url fragment (the part after #)
        if '{searchTerms}' in se_url.fragment:
            query = urllib.parse.quote_plus(query)
            se_url_frag = se_url.fragment.replace('{searchTerms}', query)
            se_url = se_url._replace(fragment=se_url_frag)
            return urllib.parse.urlunsplit(se_url)

        if '{searchTermsBase64}' in se_url.fragment:
            se_url_frag = se_url.fragment.replace('{searchTermsBase64}', b64encode(query.encode('utf-8')).decode('utf-8'))
            se_url = se_url._replace(fragment=se_url_frag)
            return urllib.parse.urlunsplit(se_url)

        # In url parameters
        se_params = urllib.parse.parse_qs(se_url.query)
        for key, val in se_params.items():
            val = val[0]
            if '{searchTerms}' in val:
                se_params[key] = [val.replace('{searchTerms}', query)]
                break
            if '{searchTermsBase64}' in val:
                se_params[key] = [val.replace('{searchTermsBase64}', b64encode(query.encode('utf-8')).decode('utf-8'))]
                break
        else:
            raise Exception('could not find {searchTerms} or {searchTermsBase64} parameter')

        se_url_query = urllib.parse.urlencode(se_params, doseq=True)
        se_url = se_url._replace(query=se_url_query)
        return urllib.parse.urlunsplit(se_url)

    @classmethod
    def should_redirect(cls, query):
        se = None
        for i, w in enumerate(query.split()):
            if not w.startswith(settings.SOSSE_SEARCH_SHORTCUT_CHAR):
                continue

            se_str = w[len(settings.SOSSE_SEARCH_SHORTCUT_CHAR):]
            if settings.SOSSE_DEFAULT_SEARCH_REDIRECT and se_str == settings.SOSSE_SOSSE_SHORTCUT:
                return

            se = SearchEngine.objects.filter(shortcut=se_str).first()
            if se is None:
                continue

            q = query.split()
            del q[i]
            query = ' '.join(q)
            break
        else:
            # Follow the default redirect if a query was provided
            if settings.SOSSE_DEFAULT_SEARCH_REDIRECT and query.strip():
                se = SearchEngine.objects.filter(short_name=settings.SOSSE_DEFAULT_SEARCH_REDIRECT).first()

        if se:
            return se.get_search_url(query)


class FavIcon(models.Model):
    url = models.TextField(unique=True)
    content = models.BinaryField(null=True, blank=True)
    mimetype = models.CharField(max_length=64, null=True, blank=True)
    missing = models.BooleanField(default=True)

    @classmethod
    def extract(cls, doc, page):
        url = cls._get_url(page)

        if url is None:
            url = '/favicon.ico'

        url = absolutize_url(doc.url, url, False, False)

        favicon, created = FavIcon.objects.get_or_create(url=url)
        doc.favicon = favicon

        if not created:
            return

        try:
            if url.startswith('data:'):
                data = url.split(':', 1)[1]
                mimetype, data = data.split(';', 1)
                encoding, data = data.split(',', 1)
                if encoding != 'base64':
                    raise Exception('encoding %s not supported' % encoding)
                data = b64decode(data)
                favicon.mimetype = mimetype
                favicon.content = data
                favicon.missing = False
            else:
                page = RequestBrowser.get(url, raw=True, check_status=True)
                from magic import from_buffer as magic_from_buffer
                favicon.mimetype = magic_from_buffer(page.content, mime=True)
                if favicon.mimetype.startswith('image/'):
                    favicon.content = page.content
                    favicon.missing = False
        except Exception:
            pass

        favicon.save()

    @classmethod
    def _get_url(cls, page):
        parsed = page.get_soup()
        links = parsed.find_all('link', rel=re.compile('shortcut icon', re.IGNORECASE))
        if links == []:
            links = parsed.find_all('link', rel=re.compile('icon', re.IGNORECASE))

        if len(links) == 0:
            return None
        if len(links) == 1:
            return links[0].get('href')

        for prefered_size in ('32x32', '16x16'):
            for link in links:
                if link.get('sizes') == prefered_size:
                    return link.get('href')

        return links[0].get('href')


class DomainSetting(models.Model):
    BROWSE_DETECT = 'detect'
    BROWSE_SELENIUM = 'selenium'
    BROWSE_REQUESTS = 'requests'
    BROWSE_MODE = [
        (BROWSE_DETECT, 'Detect'),
        (BROWSE_SELENIUM, 'Chromium'),
        (BROWSE_REQUESTS, 'Python Requests'),
    ]

    ROBOTS_UNKNOWN = 'unknown'
    ROBOTS_EMPTY = 'empty'
    ROBOTS_LOADED = 'loaded'
    ROBOTS_IGNORE = 'ignore'

    ROBOTS_STATUS = [
        (ROBOTS_UNKNOWN, 'Unknown'),
        (ROBOTS_EMPTY, 'Empty'),
        (ROBOTS_LOADED, 'Loaded'),
        (ROBOTS_IGNORE, 'Ignore')
    ]

    ROBOTS_TXT_USER_AGENT = 'user-agent'
    ROBOTS_TXT_ALLOW = 'allow'
    ROBOTS_TXT_DISALLOW = 'disallow'
    ROBOTS_TXT_KEYS = (ROBOTS_TXT_USER_AGENT, ROBOTS_TXT_ALLOW, ROBOTS_TXT_DISALLOW)

    UA_HASH = None

    browse_mode = models.CharField(max_length=10, choices=BROWSE_MODE, default=BROWSE_DETECT)
    domain = models.TextField(unique=True)

    robots_status = models.CharField(max_length=10, choices=ROBOTS_STATUS, default=ROBOTS_UNKNOWN, verbose_name='robots.txt status')
    robots_ua_hash = models.CharField(max_length=32, default='', blank=True)
    robots_allow = models.TextField(default='', blank=True, verbose_name='robots.txt allow rules')
    robots_disallow = models.TextField(default='', blank=True, verbose_name='robots.txt disallow rules')
    ignore_robots = models.BooleanField(default=False, verbose_name='Ignore robots.txt')

    def __str__(self):
        return self.domain

    @classmethod
    def ua_hash(cls):
        if cls.UA_HASH is None:
            if settings.SOSSE_USER_AGENT is not None:
                cls.UA_HASH = md5(settings.SOSSE_USER_AGENT.encode('ascii')).hexdigest()
        return cls.UA_HASH

    def _parse_line(self, line):
        if '#' in line:
            line, _ = line.split('#', 1)

        if ':' not in line:
            return None, None

        key, val = line.split(':', 1)
        key = key.strip().lower()
        val = val.strip()

        # https://github.com/google/robotstxt/blob/02bc6cdfa32db50d42563180c42aeb47042b4f0c/robots.cc#L690
        if key in ('dissallow', 'dissalow', 'disalow', 'diasllow', 'disallaw'):
            key = self.ROBOTS_TXT_DISALLOW

        if key in ('user_agent', 'user agent', 'useragent'):
            key = self.ROBOTS_TXT_USER_AGENT

        if key not in self.ROBOTS_TXT_KEYS:
            return None, None

        return key, val

    def _ua_matches(self, val):
        return val.lower() in settings.SOSSE_USER_AGENT.lower()

    def _parse_robotstxt(self, content):
        ua_rules = []
        generic_rules = []
        current_rules = None

        for line in content.splitlines():
            key, val = self._parse_line(line)

            if key is None:
                continue

            if key == self.ROBOTS_TXT_USER_AGENT:
                if self._ua_matches(val):
                    crawl_logger.debug('matching UA %s' % val)
                    current_rules = ua_rules
                elif val == '*':
                    crawl_logger.debug('global UA')
                    current_rules = generic_rules
                else:
                    current_rules = None
                continue

            if current_rules is None:
                continue

            val = re.escape(val)
            val = val.replace(r'\*', '.*')
            if val.endswith(r'\$'):
                val = val[:-2] + '$'

            current_rules.append((key, val))

        if ua_rules:
            rules = ua_rules
        elif generic_rules:
            rules = generic_rules
        else:
            rules = []

        self.robots_allow = '\n'.join([val for key, val in rules if key == self.ROBOTS_TXT_ALLOW])
        self.robots_disallow = '\n'.join([val for key, val in rules if key == self.ROBOTS_TXT_DISALLOW])

    def _load_robotstxt(self, url):
        self.robots_ua_hash = self.ua_hash()
        scheme, _ = url.split(':', 1)
        robots_url = '%s://%s/robots.txt' % (scheme, self.domain)
        crawl_logger.debug('%s: downloading %s' % (self.domain, robots_url))

        try:
            page = RequestBrowser.get(robots_url, check_status=True)
            crawl_logger.debug('%s: loading %s' % (self.domain, robots_url))
            self._parse_robotstxt(page.content)
        except requests.HTTPError:
            self.robots_status = DomainSetting.ROBOTS_EMPTY
        else:
            self.robots_status = DomainSetting.ROBOTS_LOADED
        crawl_logger.debug('%s: robots.txt %s' % (self.domain, self.robots_status))

    def robots_authorized(self, url):
        if self.ignore_robots:
            return True

        if self.robots_status == DomainSetting.ROBOTS_IGNORE:
            return True

        if self.robots_status == DomainSetting.ROBOTS_UNKNOWN or self.ua_hash() != self.robots_ua_hash:
            self._load_robotstxt(url)
            self.save()

        if self.robots_status == DomainSetting.ROBOTS_EMPTY:
            crawl_logger.debug('%s: robots.txt is empty' % self.domain)
            return True

        url = urlparse(url).path

        disallow_length = None
        for pattern in self.robots_disallow.split('\n'):
            if not pattern:
                continue
            if re.match(pattern, url):
                crawl_logger.debug('%s: matched robots.txt disallow: %s' % (url, pattern))
                disallow_length = max(disallow_length or 0, len(pattern))

        if disallow_length is None:
            crawl_logger.debug('%s: robots.txt authorized' % url)
            return True

        for pattern in self.robots_allow.split('\n'):
            if not pattern:
                continue
            if re.match(pattern, url):
                if len(pattern) > disallow_length:
                    crawl_logger.debug('%s: robots.txt authorized by allow rule' % url)
                    return True

        crawl_logger.debug('%s: robots.txt denied' % url)
        return False

    @classmethod
    def get_from_url(cls, url, default_browse_mode=None):
        domain = urlparse(url).netloc

        if not default_browse_mode:
            crawl_policy = CrawlPolicy.get_from_url(url)
            default_browse_mode = crawl_policy.default_browse_mode

        return DomainSetting.objects.get_or_create(domain=domain,
                                                   defaults={'browse_mode': default_browse_mode})[0]


class Cookie(models.Model):
    TLDS = PublicSuffixList().tlds

    SAME_SITE_LAX = 'Lax'
    SAME_SITE_STRICT = 'Strict'
    SAME_SITE_NONE = 'None'
    SAME_SITE = (
        (SAME_SITE_LAX, SAME_SITE_LAX),
        (SAME_SITE_STRICT, SAME_SITE_STRICT),
        (SAME_SITE_NONE, SAME_SITE_NONE)
    )
    domain = models.TextField(help_text='Domain name')
    domain_cc = models.TextField(help_text='Domain name attribute from the cookie', null=True, blank=True)
    inc_subdomain = models.BooleanField()
    name = models.TextField(blank=True)
    value = models.TextField(blank=True)
    path = models.TextField(default='/')
    expires = models.DateTimeField(null=True, blank=True)
    secure = models.BooleanField()
    same_site = models.CharField(max_length=6, choices=SAME_SITE, default=SAME_SITE_LAX)
    http_only = models.BooleanField(default=False)

    class Meta:
        unique_together = ('domain', 'name', 'path')

    @classmethod
    def get_from_url(cls, url, queryset=None, expire=True):
        if not url.startswith('http:') and not url.startswith('https:'):
            return []

        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        url_path = parsed_url.path

        if queryset is None:
            queryset = Cookie.objects.all()

        if not url.startswith('https://'):
            queryset = queryset.filter(secure=False)

        _cookies = queryset.filter(domain=domain)

        V = models.Value
        F = models.F
        Concat = models.functions.Concat
        Right = models.functions.Right
        Len = models.functions.Length
        dom = ''

        for sub in domain.split('.'):
            if dom != '':
                dom = '.' + dom
            dom = sub + dom
            _cookies |= queryset.filter(inc_subdomain=True).annotate(
                left=Right(V(domain), Len('domain') + 1),
                right=Concat(V('.'), 'domain', output_field=models.TextField())
            ).filter(left=F('right'))

        cookies = []
        for c in _cookies:
            cookie_path = c.path.rstrip('/')
            if cookie_path == '' or url_path.rstrip('/') == cookie_path or url_path.startswith(cookie_path + '/'):
                if expire and c.expires and c.expires <= now():
                    c.delete()
                    continue
                cookies.append(c)

        return cookies

    @classmethod
    def set(cls, url, cookies):
        crawl_logger.debug('saving cookies for %s: %s', url, cookies)
        new_cookies = []
        parsed_url = urlparse(url)
        set_cookies = [c['name'] for c in cookies]

        for c in cookies:
            name = c.pop('name')
            path = c.pop('path', '') or ''
            domain = parsed_url.hostname
            domain_cc = None

            cookie_dom = c.pop('domain', None)
            inc_subdomain = False
            if cookie_dom:
                domain_cc = cookie_dom
                cookie_dom = cookie_dom.lstrip('.')
                inc_subdomain = True

                if get_public_suffix(cookie_dom) != get_public_suffix(domain):
                    crawl_logger.warning('%s is trying to set a cookie (%s) for a different domain %s' % (url, name, cookie_dom))
                    continue

                domain = cookie_dom

            if domain in cls.TLDS:
                crawl_logger.warning('%s is trying to set a cookie (%s) for a TLD (%s)' % (url, name, domain))
                continue

            c['inc_subdomain'] = inc_subdomain
            c['domain'] = domain
            c['domain_cc'] = domain_cc

            if not c.get('same_site'):
                c['same_site'] = Cookie._meta.get_field('same_site').default
            cookie, created = Cookie.objects.update_or_create(domain=domain, path=path, name=name, defaults=c)

            if created:
                new_cookies.append(cookie)

        # delete missing cookies
        current = cls.get_from_url(url)
        for c in current:
            if c.name not in set_cookies:
                crawl_logger.debug('%s not in %s', c.name, set_cookies)
                c.delete()
        return new_cookies


BROWSER_MAP = {
    DomainSetting.BROWSE_SELENIUM: SeleniumBrowser,
    DomainSetting.BROWSE_REQUESTS: RequestBrowser,
}


class CrawlPolicy(models.Model):
    RECRAWL_NONE = 'none'
    RECRAWL_CONSTANT = 'constant'
    RECRAWL_ADAPTIVE = 'adaptive'
    RECRAWL_MODE = [
        (RECRAWL_NONE, 'Once'),
        (RECRAWL_CONSTANT, 'Constant time'),
        (RECRAWL_ADAPTIVE, 'Adaptive')
    ]

    HASH_RAW = 'raw'
    HASH_NO_NUMBERS = 'no_numbers'
    HASH_MODE = [
        (HASH_RAW, 'Hash raw content'),
        (HASH_NO_NUMBERS, 'Normalize numbers before'),
    ]

    CRAWL_ALL = 'always'
    CRAWL_ON_DEPTH = 'depth'
    CRAWL_NEVER = 'never'
    CRAWL_CONDITION = [
        (CRAWL_ALL, 'Crawl all pages'),
        (CRAWL_ON_DEPTH, 'Depending on depth'),
        (CRAWL_NEVER, 'Never crawl'),
    ]

    url_regex = models.TextField(unique=True)
    condition = models.CharField(max_length=6, choices=CRAWL_CONDITION, default=CRAWL_ALL)
    mimetype_regex = models.TextField(default='text/.*')
    crawl_depth = models.PositiveIntegerField(default=0, help_text='Level of external links (links that don\'t match the regex) to recurse into')
    keep_params = models.BooleanField(default=True, verbose_name='Index URL parameters', help_text='When disabled, URL parameters (parameters after "?") are removed from URLs, this can be useful if some parameters are random, change sorting or filtering, ...')

    default_browse_mode = models.CharField(max_length=8, choices=DomainSetting.BROWSE_MODE, default=DomainSetting.BROWSE_DETECT, help_text='Python Request is faster, but can\'t execute Javascript and may break pages')
    take_screenshots = models.BooleanField(default=False)
    screenshot_format = models.CharField(max_length=3, choices=Document.SCREENSHOT_FORMAT, default=Document.SCREENSHOT_JPG)
    script = models.TextField(default='', help_text='Javascript code to execute after the page is loaded', blank=True)
    store_extern_links = models.BooleanField(default=False)

    recrawl_mode = models.CharField(max_length=8, choices=RECRAWL_MODE, default=RECRAWL_ADAPTIVE, verbose_name='Crawl frequency', help_text='Adaptive frequency will increase delay between two crawls when the page stays unchanged')
    recrawl_dt_min = models.DurationField(blank=True, null=True, help_text='Min. time before recrawling a page', default=timedelta(days=1))
    recrawl_dt_max = models.DurationField(blank=True, null=True, help_text='Max. time before recrawling a page', default=timedelta(days=365))
    hash_mode = models.CharField(max_length=10, choices=HASH_MODE, default=HASH_NO_NUMBERS, help_text='Page content hashing method used to detect changes in the content')

    auth_login_url_re = models.TextField(null=True, blank=True, verbose_name='Login URL', help_text='A redirection to this URL will trigger authentication')
    auth_form_selector = models.TextField(null=True, blank=True, verbose_name='Form selector', help_text='CSS selector pointing to the authentication &lt;form&gt; element')

    class Meta:
        verbose_name_plural = 'crawl policies'

    def __str__(self):
        return f'「{self.url_regex}」'

    @staticmethod
    def create_default():
        # mandatory default policy
        policy, _ = CrawlPolicy.objects.get_or_create(url_regex='.*', defaults={'condition': CrawlPolicy.CRAWL_ALL})
        return policy

    @staticmethod
    def get_from_url(url):
        return CrawlPolicy.objects.extra(where=['%s ~ url_regex'], params=[url]).annotate(
            url_regex_len=models.functions.Length('url_regex')
        ).order_by('-url_regex_len').first()

    def url_get(self, domain_setting, url):
        if self.default_browse_mode == DomainSetting.BROWSE_DETECT:
            if domain_setting.browse_mode in (DomainSetting.BROWSE_DETECT, DomainSetting.BROWSE_SELENIUM):
                browser = SeleniumBrowser
            elif domain_setting.browse_mode == DomainSetting.BROWSE_REQUESTS:
                browser = RequestBrowser
            else:
                raise Exception('Unsupported browse_mode')
        else:
            browser = BROWSER_MAP[self.default_browse_mode]

        page = browser.get(url)

        if page.redirect_count:
            # The request was redirected, check if we need auth
            try:
                crawl_logger.debug('may auth %s / %s' % (page.url, self.auth_login_url_re))
                if self.auth_login_url_re and \
                        self.auth_form_selector and \
                        re.search(self.auth_login_url_re, page.url):
                    crawl_logger.debug('doing auth for %s' % url)
                    new_page = page.browser.try_auth(page, url, self)

                    if new_page.url != url:
                        crawl_logger.debug('reopening %s after auth' % url)
                        page = browser.get(url)
                    else:
                        page = new_page
            except Exception as e:  # noqa
                if isinstance(e, AuthElemFailed):
                    raise
                raise Exception('Authentication failed')

        if domain_setting.browse_mode == DomainSetting.BROWSE_DETECT:
            crawl_logger.debug('browser detection on %s' % url)
            requests_page = RequestBrowser.get(url)

            if len(list(requests_page.get_links(self))) != len(list(page.get_links(self))):
                new_mode = DomainSetting.BROWSE_SELENIUM
            else:
                new_mode = DomainSetting.BROWSE_REQUESTS
                page = requests_page
            crawl_logger.debug('browser detected %s on %s' % (new_mode, url))
            domain_setting.browse_mode = new_mode
            domain_setting.save()
        return page


class SearchHistory(models.Model):
    query = models.TextField()
    querystring = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @classmethod
    def save_history(cls, request, q):
        from .search import FILTER_RE
        params = {}

        queryparams = ''
        for key, val in request.GET.items():
            if not re.match(FILTER_RE, key) and \
                    key not in ('l', 'doc_lang', 's', 'q'):
                continue
            params[key] = val

            if not key.startswith('fv'):
                continue

            if queryparams:
                queryparams += ' '
            queryparams += val

        if q:
            if queryparams:
                q = '%s (%s)' % (q, queryparams)
        else:
            q = queryparams

        qd = QueryDict(mutable=True)
        qd.update(params)
        qs = qd.urlencode()

        if not request.user.is_anonymous:
            last = SearchHistory.objects.filter(user=request.user).order_by('date').last()
            if last and last.querystring == qs:
                return

            if not q and not qs:
                return

            SearchHistory.objects.create(querystring=qs,
                                         query=q,
                                         user=request.user)


class ExcludedUrl(models.Model):
    url = models.TextField(unique=True)
    comment = models.TextField(blank=True, null=True)
