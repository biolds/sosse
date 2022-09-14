import json
import os
import re
import urllib.parse
import unicodedata
import logging

from base64 import b64decode
from datetime import date, datetime, timedelta
from defusedxml import ElementTree
from hashlib import md5
from time import sleep
from traceback import format_exc
from urllib.parse import urlparse

from bs4 import Doctype, Tag
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import connection, models
from django.http import QueryDict
from django.shortcuts import reverse
from django.utils.timezone import now
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from magic import from_buffer as magic_from_buffer
import requests

from .browser import RequestBrowser, SeleniumBrowser

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
    if p.startswith('/'):
        new_path = p
    else:
        new_path = os.path.dirname(url.path)
        new_path += '/' + p

    url = url._replace(path=new_path)
    return sanitize_url(url.geturl(), keep_params, keep_anchors)


def remove_accent(s):
    # append an ascii version to match on non-accented letters
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


class RegConfigField(models.Field):
    def db_type(self, connection):
        return 'regconfig'


class Document(models.Model):
    # Document info
    url = models.TextField(unique=True)

    normalized_url = models.TextField()
    title = models.TextField()
    normalized_title = models.TextField()
    content = models.TextField()
    normalized_content = models.TextField()
    content_hash = models.CharField(max_length=128, null=True, blank=True)
    vector = SearchVectorField(null=True, blank=True)
    lang_iso_639_1 = models.CharField(max_length=6, null=True, blank=True)
    vector_lang = RegConfigField(default='simple')

    favicon = models.ForeignKey('FavIcon', null=True, blank=True, on_delete=models.SET_NULL)
    robotstxt_rejected = models.BooleanField(default=False)

    # HTTP status
    redirect_url = models.TextField(null=True, blank=True)

    screenshot_file = models.CharField(max_length=4096, blank=True, null=True)
    screenshot_count = models.PositiveIntegerField(blank=True, null=True)

    # Crawling info
    crawl_first = models.DateTimeField(blank=True, null=True)
    crawl_last = models.DateTimeField(blank=True, null=True)
    crawl_next = models.DateTimeField(blank=True, null=True)
    crawl_dt = models.DurationField(blank=True, null=True)
    crawl_depth = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default='')
    error_hash = models.TextField(blank=True, default='')
    worker_no = models.PositiveIntegerField(blank=True, null=True)

    supported_langs = None

    class Meta:
        indexes = [GinIndex(fields=(('vector',)))]

    def get_absolute_url(self):
        if self.screenshot_file:
            return reverse('screenshot', args=(self.url,))
        else:
            return reverse('www', args=(self.url,))

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
        for iso, lang in settings.OSSE_LANGDETECT_TO_POSTGRES.items():
            if lang['name'] in supported:
                langs[iso] = lang
        return langs

    @classmethod
    def _get_lang(cls, text):
        try:
            lang_iso = detect(text)
        except LangDetectException:
            lang_iso = None

        lang_pg = settings.OSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')
        if lang_pg not in cls.get_supported_langs():
            lang_pg = settings.OSSE_FAIL_OVER_LANG

        return lang_iso, lang_pg

    def _hash_content(self, content, url_policy):
        if url_policy.hash_mode == UrlPolicy.HASH_RAW:
            pass
        elif url_policy.hash_mode == UrlPolicy.HASH_NO_NUMBERS:
            content = re.sub('[0-9]+', '0', content)
        else:
            raise Exception('HASH_MODE not supported')

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

    def _dom_walk(self, elem, url_policy, links):
        if isinstance(elem, Doctype):
            return

        if elem.name in ('[document]', 'title', 'script', 'style'):
            return

        s = getattr(elem, 'string', None)
        if s is not None:
            s = s.strip(' \t\n\r')

        # Keep the link if it has text, or if we take screenshots
        if elem.name in (None, 'a') and (s or url_policy.take_screenshots):
            if links['text'] and links['text'][-1] not in (' ', '\n'):
                links['text'] += ' '

            if elem.name == 'a':
                href = elem.get('href')
                if href:
                    href = href.strip()

                    href_for_policy = absolutize_url(self.url, href, True, True)
                    child_policy = UrlPolicy.get_from_url(href_for_policy)
                    href = absolutize_url(self.url, href, child_policy.keep_params, False)
                    target = Document.queue(href, url_policy, self)
                    link = None
                    if target:
                        link = Link(doc_from=self,
                                    link_no=len(links['links']),
                                    doc_to=target,
                                    text=s,
                                    pos=len(links['text']))
                    elif url_policy.store_extern_links:
                        href = elem.get('href').strip()
                        href = absolutize_url(self.url, href, True, True)
                        link = Link(doc_from=self,
                                    link_no=len(links['links']),
                                    text=s,
                                    pos=len(links['text']),
                                    extern_url=href)

                    if link:
                        if url_policy.take_screenshots:
                            link.css_selector = self._build_selector(elem)
                        links['links'].append(link)

            if s:
                links['text'] += s

            if elem.name == 'a':
                return

        if hasattr(elem, 'children'):
            for child in elem.children:
                self._dom_walk(child, url_policy, links)

        if elem.name in ('div', 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            if links['text']:
                if links['text'][-1] == ' ':
                    links['text'] = links['text'][:-1] + '\n'
                elif links['text'][-1] != '\n':
                    links['text'] += '\n'

    def index(self, page, url_policy, verbose=False, force=False):
        n = now()
        stats = {'prev': n}
        content_hash = self._hash_content(page.content, url_policy)
        self._index_log('hash', stats, verbose)

        self.crawl_last = n
        if not self.crawl_first:
            self.crawl_first = n
        self._schedule_next(self.content_hash != content_hash)
        if self.content_hash == content_hash and not force:
            return

        self.content_hash = content_hash
        self._index_log('queuing links', stats, verbose)

        self.normalized_url = page.url.split('://', 1)[1].replace('/', ' ')

        parsed = page.get_soup()
        self.title = page.title or self.url
        self.normalized_title = remove_accent(self.title)
        self._index_log('get soup', stats, verbose)

        links = {
            'links': [],
            'text': ''
        }
        for elem in parsed.children:
            self._dom_walk(elem, url_policy, links)
        text = links['text']

        self._index_log('text / %i links extraction' % len(links['links']), stats, verbose)

        self.content = text
        self.normalized_content = remove_accent(text)
        self.lang_iso_639_1, self.vector_lang = self._get_lang((page.title or '') + '\n' + text)
        self._index_log('remove accent', stats, verbose)

        FavIcon.extract(self, page)
        self._index_log('favicon', stats, verbose)

        if url_policy.take_screenshots:
            self.screenshot_index(links['links'])

        Link.objects.filter(doc_from=self).delete()
        self._index_log('delete', stats, verbose)

        # The bulk request triggers a deadlock
        #Link.objects.bulk_create(links['links'])
        for link in links['links']:
            link.save()
        self._index_log('bulk', stats, verbose)

    def screenshot_index(self, links):
        filename, img_count = SeleniumBrowser.take_screenshots(self.url)
        self.screenshot_file = filename
        self.screenshot_count = img_count

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

    def set_error(self, err):
        self.error = err
        if err == '':
            self.error_hash = ''
        else:
            self.error_hash = md5(err.encode('utf-8')).hexdigest()

    @staticmethod
    def queue(url, parent_policy, parent):
        url_policy = UrlPolicy.get_from_url(url)
        crawl_logger.debug('%s matched %s, %s' % (url, url_policy.url_regex, url_policy.crawl_when))

        if url_policy.crawl_when == UrlPolicy.CRAWL_ALWAYS or parent is None:
            crawl_logger.debug('%s -> always crawl' % url)
            return Document.objects.get_or_create(url=url)[0]

        if url_policy.crawl_when == UrlPolicy.CRAWL_NEVER:
            crawl_logger.debug('%s -> never crawl' % url)
            return None

        doc = None
        url_depth = None

        if parent_policy.crawl_when == UrlPolicy.CRAWL_ALWAYS and parent_policy.crawl_depth > 0:
            doc = Document.objects.get_or_create(url=url)[0]
            url_depth = max(parent_policy.crawl_depth, doc.crawl_depth)
            crawl_logger.debug('%s -> recurse for %s' % (url, url_depth))
        elif parent_policy.crawl_when == UrlPolicy.CRAWL_ON_DEPTH and parent.crawl_depth > 1:
            doc = Document.objects.get_or_create(url=url)[0]
            url_depth = max(parent.crawl_depth - 1, doc.crawl_depth)
            crawl_logger.debug('%s -> recurse at %s' % (url, url_depth))
        else:
            crawl_logger.debug('%s -> no recurse (from parent %s)' % (url, parent_policy.crawl_when))

        if doc and url_depth != doc.crawl_depth:
            doc.crawl_depth = url_depth
            doc.save()

        return doc

    def _schedule_next(self, changed):
        url_policy = UrlPolicy.get_from_url(self.url)
        if url_policy.recrawl_mode == UrlPolicy.RECRAWL_NONE:
            self.crawl_next = None
            self.crawl_dt = None
        elif url_policy.recrawl_mode == UrlPolicy.RECRAWL_CONSTANT:
            self.crawl_next = self.crawl_last + url_policy.recrawl_dt_min
            self.crawl_dt = None
        elif url_policy.recrawl_mode == UrlPolicy.RECRAWL_ADAPTIVE:
            if self.crawl_dt is None:
                self.crawl_dt = url_policy.recrawl_dt_min
            elif not changed:
                self.crawl_dt = min(url_policy.recrawl_dt_max, self.crawl_dt * 2)
            else:
                self.crawl_dt = max(url_policy.recrawl_dt_min, self.crawl_dt / 2)
            self.crawl_next = self.crawl_last + self.crawl_dt

    @staticmethod
    def crawl(worker_no):
        doc = Document.pick_queued(worker_no)
        if doc is None:
            return False

        worker_stats, _ = WorkerStats.objects.get_or_create(defaults={'doc_processed': 0}, worker_no=worker_no)

        crawl_logger.info('Worker:%i Queued:%i Indexed:%i Id:%i %s ...' % (worker_no,
                                        Document.objects.filter(crawl_last__isnull=True).count(),
                                        Document.objects.filter(crawl_last__isnull=False).count(),
                                        doc.id, doc.url))

        while True:
            try:
                worker_stats.doc_processed += 1
                doc.worker_no = None
                doc.crawl_last = now()

                if doc.url.startswith('http://') or doc.url.startswith('https://'):
                    url_policy = UrlPolicy.get_from_url(doc.url)
                    domain = urlparse(doc.url).netloc
                    domain_setting, _ = DomainSetting.objects.get_or_create(domain=domain,
                                                                            defaults={'browse_mode': url_policy.default_browse_mode})
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

                    page = url_policy.url_get(domain_setting, doc.url)

                    if page.url == doc.url:
                        doc.index(page, url_policy)
                        doc.set_error('')
                        break
                    else:
                        if not page.got_redirect:
                            raise Exception('redirect not set %s -> %s' % (doc.url, page.url))
                        crawl_logger.debug('%i redirect %s -> %s' % (worker_no, doc.url, page.url))
                        doc._schedule_next(doc.redirect_url != page.url)
                        doc.redirect_url = page.url
                        doc.save()
                        doc = Document.pick_or_create(page.url, worker_no)
                        if doc is None:
                            break

            except Exception as e:
                doc.set_error(format_exc())
                doc.save()
                crawl_logger.error(format_exc())
                break

        if doc:
            doc.save()

        worker_stats.save()
        return True

    @staticmethod
    def pick_queued(worker_no):
        while True:
            doc = Document.objects.filter(worker_no__isnull=True,
                                          crawl_last__isnull=True).first()
            if doc is None:
                doc = Document.objects.filter(worker_no__isnull=True,
                                              crawl_last__isnull=False,
                                              crawl_next__lte=now()).order_by('crawl_next').first()
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
    key = models.CharField(max_length=256)
    value = models.CharField(max_length=256)
    url_policy = models.ForeignKey('UrlPolicy', on_delete=models.CASCADE)

    def __str__(self):
        return '%s form field' % self.key


MINUTELY = 'M'
DAILY = 'D'
FREQUENCY = (
    (MINUTELY, MINUTELY),
    (DAILY, DAILY),
)


class WorkerStats(models.Model):
    doc_processed = models.PositiveIntegerField()
    worker_no = models.IntegerField()


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
        WorkerStats.objects.filter().update(doc_processed=0)

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


class SearchEngine(models.Model):
    short_name = models.CharField(max_length=32, blank=True, default='')
    long_name = models.CharField(max_length=48, blank=True, default='')
    description = models.CharField(max_length=1024, blank=True, default='')
    html_template = models.CharField(max_length=2048)
    shortcut = models.CharField(max_length=16, blank=True)

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

        if '{searchTerms}' in se_url.path:
            query = urllib.parse.quote_plus(query)
            se_url_path = se_url.path.replace('{searchTerms}', query)
            se_url = se_url._replace(path=se_url_path)
            return urllib.parse.urlunsplit(se_url)

        se_params = urllib.parse.parse_qs(se_url.query)
        for key, val in se_params.items():
            val = val[0]
            if '{searchTerms}' in val:
                se_params[key] = [val.replace('{searchTerms}', query)]
                break
        else:
            raise Exception('could not find {searchTerms} parameter')

        se_url_query = urllib.parse.urlencode(se_params, doseq=True)
        se_url = se_url._replace(query=se_url_query)
        return urllib.parse.urlunsplit(se_url)

    @classmethod
    def should_redirect(cls, query):
        for i, w in enumerate(query.split()):
            if not w.startswith('!'):
                continue
            try:
                se = SearchEngine.objects.get(shortcut=w[1:])

                q = query.split()
                del q[i]
                return se.get_search_url(' '.join(q))
            except SearchEngine.DoesNotExist:
                pass


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

        url = absolutize_url(doc.url, url, True, False)

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
        (BROWSE_REQUESTS, 'Python Requests (faster)'),
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
    domain = models.TextField()

    robots_status = models.CharField(max_length=10, choices=ROBOTS_STATUS, default=ROBOTS_UNKNOWN)
    robots_ua_hash = models.CharField(max_length=32, default='', blank=True)
    robots_allow = models.TextField(default='', blank=True)
    robots_disallow = models.TextField(default='', blank=True)

    def __str__(self):
        return '%s %s' % (self.domain, self.browse_mode)

    @classmethod
    def ua_hash(cls):
        if cls.UA_HASH is None:
            if settings.OSSE_USER_AGENT is not None:
                cls.UA_HASH = md5(settings.OSSE_USER_AGENT.encode('ascii')).hexdigest()
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
        return val.lower() in settings.OSSE_USER_AGENT.lower()

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

    def _load_robotstxt(self):
        crawl_logger.debug('loading robots txt')
        self.robots_ua_hash = self.ua_hash()

        try:
            page = RequestBrowser.get('http://%s/robots.txt' % self.domain, check_status=True)
            self._parse_robotstxt(page.content)
        except requests.HTTPError:
            self.robots_status = DomainSetting.ROBOTS_EMPTY
        else:
            self.robots_status = DomainSetting.ROBOTS_LOADED


    def robots_authorized(self, url):
        if self.robots_status == DomainSetting.ROBOTS_IGNORE:
            return True

        if self.robots_status == DomainSetting.ROBOTS_UNKNOWN or self.ua_hash() != self.robots_ua_hash:
            self._load_robotstxt()
            self.save()

        if self.robots_status == DomainSetting.ROBOTS_EMPTY:
            return True

        url = urlparse(url).path

        disallow_length = None
        for pattern in self.robots_disallow.split('\n'):
            if re.match(pattern, url):
               disallow_length = max(disallow_length or 0, len(pattern))

        if disallow_length is None:
            return True

        for pattern in self.robots_allow.split('\n'):
            if re.match(pattern, url):
               if len(pattern) > disallow_length:
                    return True

        return False


class UrlPolicy(models.Model):
    RECRAWL_NONE = 'none'
    RECRAWL_CONSTANT = 'constant'
    RECRAWL_ADAPTIVE = 'adaptive'
    RECRAWL_MODE = [
        (RECRAWL_NONE, 'No recrawl'),
        (RECRAWL_CONSTANT, 'Constant time'),
        (RECRAWL_ADAPTIVE, 'Adaptive')
    ]

    HASH_RAW = 'raw'
    HASH_NO_NUMBERS = 'no_numbers'
    HASH_MODE = [
        (HASH_RAW, 'Hash raw content'),
        (HASH_NO_NUMBERS, 'Normalize numbers before'),
    ]

    CRAWL_ALWAYS = 'always'
    CRAWL_ON_DEPTH = 'depth'
    CRAWL_NEVER = 'never'
    CRAWL_WHEN = [
        (CRAWL_ALWAYS, 'Always'),
        (CRAWL_ON_DEPTH, 'Depending on depth'),
        (CRAWL_NEVER, 'Never'),
    ]

    url_regex = models.TextField(unique=True)
    crawl_when = models.CharField(max_length=6, choices=CRAWL_WHEN, default=CRAWL_ALWAYS)

    default_browse_mode = models.CharField(max_length=8, choices=DomainSetting.BROWSE_MODE, default=DomainSetting.BROWSE_DETECT)
    recrawl_mode = models.CharField(max_length=8, choices=RECRAWL_MODE, default=RECRAWL_ADAPTIVE)
    recrawl_dt_min = models.DurationField(blank=True, null=True, help_text='Min. time before recrawling a page', default=timedelta(minutes=1))
    recrawl_dt_max = models.DurationField(blank=True, null=True, help_text='Max. time before recrawling a page', default=timedelta(days=365))
    crawl_depth = models.PositiveIntegerField(default=0)

    store_extern_links = models.BooleanField(default=False)
    keep_params = models.BooleanField(default=False)

    hash_mode = models.CharField(max_length=10, choices=HASH_MODE, default=HASH_NO_NUMBERS)

    auth_login_url_re = models.TextField(null=True, blank=True)
    auth_form_selector = models.TextField(null=True, blank=True)
    auth_cookies = models.TextField(blank=True, default='')

    take_screenshots = models.BooleanField(default=False)

    def __str__(self):
        return f'<{self.url_regex}>'

    @staticmethod
    def get_from_url(url):
        return UrlPolicy.objects.extra(where=['%s ~ url_regex'], params=[url]).annotate(
            url_regex_len=models.functions.Length('url_regex')
        ).order_by('-url_regex_len').first()

    def url_get(self, domain_setting, url):
        if domain_setting.browse_mode in (DomainSetting.BROWSE_DETECT, DomainSetting.BROWSE_SELENIUM):
            browser = SeleniumBrowser
        elif domain_setting.browse_mode == DomainSetting.BROWSE_REQUESTS:
            browser = RequestBrowser
        else:
            raise Exception('Unsupported browse_mode')

        page = browser.get(url)

        if page.got_redirect:
            # The request was redirected, check if we need auth
            try:
                crawl_logger.debug('may auth %s / %s' % (page.url, self.auth_login_url_re))
                if self.auth_login_url_re and \
                        self.auth_form_selector and \
                        re.search(self.auth_login_url_re, page.url) :
                    crawl_logger.debug('doing auth on %s' % url)
                    new_page = page.browser.try_auth(page, url, self)
                    new_page.got_redirect = True

                    if new_page:
                        page = new_page
            except:
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

    @staticmethod
    def get_cookies(url):
        try:
            cookies = UrlPolicy.get_from_url(url).auth_cookies
            if cookies:
                return json.loads(cookies)
        except UrlPolicy.DoesNotExist:
            pass


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

        last = SearchHistory.objects.filter(user=request.user).order_by('date').last()
        if last and last.querystring == qs:
            return

        if not q and not qs:
            return

        SearchHistory.objects.create(querystring=qs,
                                     query=q,
                                     user=request.user)
