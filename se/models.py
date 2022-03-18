import json
import os
import re
import urllib.parse
import unicodedata

from base64 import b64decode
from datetime import date, datetime, timedelta
from defusedxml import ElementTree
from hashlib import md5
from time import sleep
from traceback import format_exc
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import connection, models
from django.utils.timezone import now
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from magic import from_buffer as magic_from_buffer
import requests

from .browser import RequestBrowser, SeleniumBrowser

DetectorFactory.seed = 0


def sanitize_url(url):
    for to_del in ('?', '#'):
        if to_del in url:
            url = url.split(to_del, 1)[0]

    url = urlparse(url)

    if url.path == '':
        url = url._replace(path='/')
    else:
        new_path = os.path.abspath(url.path)
        new_path = new_path.replace('//', '/')
        url = url._replace(path=new_path)

    url = url.geturl()
    return url


def absolutize_url(url, p):
    if p.startswith('data:'):
        return p

    if p == '':
        return sanitize_url(url)

    if re.match('[a-zA-Z]+:', p):
        return sanitize_url(p)

    url = urlparse(url)
    if p.startswith('/'):
        new_path = p
    else:
        new_path = os.path.dirname(url.path)
        new_path += '/' + p

    url = url._replace(path=new_path)
    return sanitize_url(url.geturl())


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

    # HTTP status
    redirect_url = models.TextField(null=True, blank=True)

    # Crawling info
    crawl_first = models.DateTimeField(blank=True, null=True)
    crawl_last = models.DateTimeField(blank=True, null=True)
    crawl_next = models.DateTimeField(blank=True, null=True)
    crawl_dt = models.DurationField(blank=True, null=True)
    error = models.TextField(blank=True, default='')
    error_hash = models.TextField(blank=True, default='')
    worker_no = models.PositiveIntegerField(blank=True, null=True)

    supported_langs = None

    class Meta:
        indexes = [GinIndex(fields=(('vector',)))]

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
        for iso, lang in settings.MYSE_LANGDETECT_TO_POSTGRES.items():
            if lang['name'] in supported:
                langs[iso] = lang
        return langs

    @classmethod
    def _get_lang(cls, text):
        try:
            lang_iso = detect(text)
        except LangDetectException:
            lang_iso = None

        lang_pg = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')
        if lang_pg not in cls.get_supported_langs():
            lang_pg = settings.MYSE_FAIL_OVER_LANG

        return lang_iso, lang_pg

    def _hash_content(self, content, domain_policy):
        if domain_policy.hash_mode == DomainPolicy.HASH_RAW:
            pass
        elif domain_policy.hash_mode == DomainPolicy.HASH_NO_NUMBERS:
            content = re.sub('[0-9]+', '0', content)
        else:
            raise Exception('HASH_MODE not supported')

        return settings.HASHING_ALGO(content.encode('utf-8')).hexdigest()


    def index(self, page, domain_policy):
        content_hash = self._hash_content(page.content, domain_policy)
        n = now()
        self.crawl_last = n
        if not self.crawl_first:
            self.crawl_first = n
        self._schedule_next(self.content_hash != content_hash)
        if self.content_hash == content_hash:
            return

        self.content_hash = content_hash

        for link in page.get_links():
            Document.queue(link)

        self.normalized_url = page.url.split('://', 1)[1].replace('/', ' ')

        parsed = page.get_soup()
        self.title = page.title or self.url
        self.normalized_title = remove_accent(self.title)

        text = ''

        link_no = 0
        for elem in parsed.descendants:
            if not elem.string:
                continue

            s = str(elem.string).strip(' \t\n\r')
            if not s:
                continue

            if elem.name == 'a' and domain_policy.store_links:
                if text != '':
                    text += '\n'
                text += s

                href = elem.get('href')
                if not href:
                    continue

                href = absolutize_url(self.url, href)
                try:
                    target = Document.objects.get(url=href)
                except Document.DoesNotExist:
                    continue

                link, _ = Link.objects.get_or_create(doc_from=self,
                                                     link_no=link_no,
                                                     defaults={
                                                        'doc_to': target,
                                                        'text': s,
                                                        'pos': len(text) - len(s)
                                                     })
                link.doc_to = target
                link.text = s
                link.pos = len(text) - len(s)
                link.save()
                link_no += 1

            if elem.parent and elem.parent.name == 'a' and domain_policy.store_links:
                continue

            if elem.parent and elem.parent.name in ('[document]', 'title'):
                # this element [document] contains a "html" string, not sure why
                continue
            if elem.name is not None:
                continue

            if text != '':
                text += '\n'

            if s == 'html':
                raise Exception('%s %s' % (elem.parent.name, elem.name))
            text += s

        if domain_policy.store_links:
            Link.objects.filter(doc_from=self, link_no__gte=link_no).delete()

        self.content = text
        self.normalized_content = remove_accent(text)
        self.lang_iso_639_1, self.vector_lang = self._get_lang((page.title or '') + '\n' + text)

        FavIcon.extract(self, page)

    def set_error(self, err):
        self.error = err
        if err == '':
            self.error_hash = ''
        else:
            self.error_hash = md5(err.encode('utf-8')).hexdigest()

    @staticmethod
    def queue(url):
        try:
            doc = Document.objects.get(url=url)
            return doc
        except Document.DoesNotExist:
            pass

        for w in QueueWhitelist.objects.all():
            if url.startswith(w.url):
                break
        else:
            return

        doc, _ = Document.objects.get_or_create(url=url)
        doc.save()
        return doc

    def _schedule_next(self, changed):
        domain_policy = DomainPolicy.get_from_url(self.url)
        if domain_policy.recrawl_mode == DomainPolicy.RECRAWL_NONE:
            self.crawl_next = None
            self.crawl_dt = None
        elif domain_policy.recrawl_mode == DomainPolicy.RECRAWL_CONSTANT:
            self.crawl_next = self.crawl_last + timedelta(minutes=domain_policy.recrawl_dt_min)
            self.crawl_dt = None
        elif domain_policy.recrawl_mode == DomainPolicy.RECRAWL_ADAPTIVE:
            if self.crawl_dt is None:
                self.crawl_dt = timedelta(minutes=domain_policy.recrawl_dt_min)
            elif not changed:
                self.crawl_dt = min(timedelta(minutes=domain_policy.recrawl_dt_max), self.crawl_dt * 2)
            else:
                self.crawl_dt = max(timedelta(minutes=domain_policy.recrawl_dt_min), self.crawl_dt / 2)
            self.crawl_next = self.crawl_last + self.crawl_dt

    @staticmethod
    def crawl(worker_no):
        doc = Document.pick_queued(worker_no)
        if doc is None:
            return False

        worker_stats, _ = WorkerStats.objects.get_or_create(defaults={'doc_processed': 0}, worker_no=worker_no)

        print('%i (%i/%i) %i %s ...' % (worker_no,
                                        Document.objects.filter(crawl_last__isnull=True).count(),
                                        Document.objects.filter(crawl_last__isnull=False).count(),
                                        doc.id, doc.url))

        while True:
            try:
                worker_stats.doc_processed += 1
                doc.worker_no = None

                if doc.url.startswith('http://') or doc.url.startswith('https://'):
                    domain_policy = DomainPolicy.get_from_url(doc.url)
                    page = domain_policy.url_get(doc.url)

                    if page.url == doc.url:
                        doc.index(page, domain_policy)
                        break
                    else:
                        if not page.got_redirect:
                            raise Exception('redirect not set %s -> %s' % (doc.url, page.url))
                        print('%i redirect %s -> %s' % (worker_no, doc.url, page.url))
                        doc.redirect_url = page.url
                        doc.save()
                        doc = Document.pick_or_create(page.url, worker_no)
                        if doc is None:
                            break

            except Exception as e:
                doc.set_error(format_exc())
                doc.save()
                print(format_exc())
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
    doc_from = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='links_to')
    doc_to = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='linked_from')
    text = models.TextField()
    pos = models.PositiveIntegerField()
    link_no = models.PositiveIntegerField()

    class Meta:
        unique_together = ('doc_from', 'doc_to', 'link_no')

class QueueWhitelist(models.Model):
    url = models.TextField(unique=True)

    def __str__(self):
        return self.url


class AuthField(models.Model):
    key = models.CharField(max_length=256)
    value = models.CharField(max_length=256)
    domain_policy = models.ForeignKey('DomainPolicy', on_delete=models.CASCADE)

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
    missing = models.BooleanField(default=False)

    @classmethod
    def extract(cls, doc, page):
        url = cls._get_url(page)

        if url is None:
            url = '/favicon.ico'

        url = absolutize_url(doc.url, url)

        favicon, created = FavIcon.objects.get_or_create(url=url)
        doc.favicon = favicon

        if not created:
            return

        favicon.missing = True

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
                favicon.save()
            else:
                page = RequestBrowser.get(url, raw=True)
                favicon.mimetype = magic_from_buffer(page.content, mime=True)
                favicon.content = page.content
                favicon.save()
            favicon.missing = False
        except Exception:
            pass

        favicon.save()

    @classmethod
    def _get_url(cls, page):
        parsed = page.get_soup()
        links = parsed.find_all('link', rel="shortcut icon")
        if links == []:
            links = parsed.find_all('link', rel="icon")

        if len(links) == 0:
            return None
        if len(links) == 1:
            return links[0].get('href')

        for prefered_size in ('32x32', '16x16'):
            for link in links:
                if link.get('sizes') == prefered_size:
                    return link.get('href')

        return links[0].get('href')


class DomainPolicy(models.Model):
    SELENIUM = 'selenium'
    REQUESTS = 'requests'
    DETECT = 'detect'
    MODE = [
        (SELENIUM, 'Selenium'),
        (REQUESTS, 'Requests'),
        (DETECT, 'Detect')
    ]

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

    url_prefix = models.TextField(unique=True)
    browse_mode = models.CharField(max_length=10, choices=MODE, default=DETECT)
    recrawl_mode = models.CharField(max_length=10, choices=RECRAWL_MODE, default=RECRAWL_ADAPTIVE)
    recrawl_dt_min = models.PositiveIntegerField(null=True, blank=True, help_text='Min. time before recrawling a page (in minutes)', default=60)
    recrawl_dt_max = models.PositiveIntegerField(null=True, blank=True, help_text='Max. time before recrawling a page (in minutes)', default=50 * 24 * 365)

    store_links = models.BooleanField(default=True)
    hash_mode = models.CharField(max_length=10, choices=HASH_MODE, default=HASH_NO_NUMBERS)

    auth_login_url_re = models.TextField(null=True, blank=True)
    auth_form_selector = models.TextField(null=True, blank=True)
    auth_cookies = models.TextField(blank=True, default='')

    def __str__(self):
        return '%s %s' % (self.url_prefix, self.browse_mode)

    def _get_browser(self):
        if self.browse_mode == DomainPolicy.SELENIUM:
            return SeleniumBrowser
        if self.browse_mode == DomainPolicy.REQUESTS:
            return RequestBrowser
        if self.browse_mode in (DomainPolicy.SELENIUM, DomainPolicy.DETECT):
            return SeleniumBrowser
        return RequestBrowser

    @staticmethod
    def get_from_url(url):
        return DomainPolicy.objects.filter(
            url_prefix=models.functions.Substr(
                models.Value(url), 1, models.functions.Length('url_prefix')
            )
        ).annotate(
            url_prefix_len=models.functions.Length('url_prefix')
        ).order_by('-url_prefix_len').first()

    def url_get(self, url):
        browser = self._get_browser()
        page = browser.get(url)

        if page.got_redirect:
            # The request was redirected, check if we need auth
            try:
                #raise Exception('%s\n%s\n%s' % (self.auth_login_url_re, page.url, self.auth_form_selector))
                if self.auth_login_url_re and \
                        self.auth_form_selector and \
                        re.search(self.auth_login_url_re, page.url) :
                    print('doing auth on %s' % url)
                    new_page = page.browser.try_auth(page, url, self)

                    if new_page:
                        page = new_page
            except:
                raise Exception('Authentication failed')

        if self.browse_mode == DomainPolicy.DETECT:
            print('browser detection on %s' % url)
            requests_page = RequestBrowser.get(url)

            if len(list(requests_page.get_links())) != len(list(page.get_links())):
                self.browse_mode = DomainPolicy.SELENIUM
            else:
                self.browse_mode = DomainPolicy.REQUESTS
                page = requests_page
            print('browser detected %s on %s' % (self.browse_mode, url))
            self.save()

        return page

    @staticmethod
    def get_cookies(url):
        try:
            cookies = DomainPolicy.get_from_url(url).auth_cookies
            if cookies:
                return json.loads(cookies)
        except DomainPolicy.DoesNotExist:
            pass
