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
from magic import from_buffer as magic_from_buffer

from .browser import RequestBrowser, SeleniumBrowser

DetectorFactory.seed = 0


def absolutize_url(url, p):
    for to_del in ('?', '#'):
        if to_del in p:
            p = p.split(to_del, 1)[0]

    if p == '':
        return url

    if re.match('[a-zA-Z]+:', p):
        return p

    url = urlparse(url)

    if p.startswith('/'):
        new_path = p
    else:
        new_path = os.path.dirname(url.path)
        new_path += '/' + p

    url = url._replace(path=new_path)
    return url.geturl()


def remove_accent(s):
    # append an ascii version to match on non-accented letters
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


class RegConfigField(models.Field):
    def db_type(self, connection):
        return 'regconfig'


class Document(models.Model):
    crawl_id = models.UUIDField(editable=False)
    url = models.TextField(unique=True)
    normalized_url = models.TextField()
    title = models.TextField()
    normalized_title = models.TextField()
    content = models.TextField()
    normalized_content = models.TextField()
    vector = SearchVectorField()
    lang_iso_639_1 = models.CharField(max_length=6, null=True, blank=True)
    vector_lang = RegConfigField(default='simple')
    favicon = models.ForeignKey('FavIcon', null=True, blank=True, on_delete=models.SET_NULL)

    supported_langs = None

    class Meta:
        indexes = [GinIndex(fields=(('vector',)))]

    def get_policy(self):
        url = absolutize_url(self.url, '/')
        policy, _ = DomainPolicy.objects.get_or_create(url=url)
        return policy

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
        lang_iso = detect(text)
        lang_pg = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')
        if lang_pg not in cls.get_supported_langs():
            lang_pg = settings.MYSE_FAIL_OVER_LANG

        return lang_iso, lang_pg

    def index(self, page, crawl_id):
        for link in page.get_links():
            UrlQueue.queue(link, crawl_id)

        parsed = page.get_soup()
        self.title = page.title or self.url
        self.normalized_title = remove_accent(self.title + '\n' + self.url)

        text = ''
        no = 0
        for i, string in enumerate(parsed.strings):
            s = string.strip(' \t\n\r')
            if s != '':
                if string == page.title and no == 0:
                    continue
                if text != '':
                    text += '\n'
                text += s
                no += 1
        self.content = text
        self.normalized_content = remove_accent(text)
        self.lang_iso_639_1, self.vector_lang = self._get_lang((page.title or '') + '\n' + text)

        FavIcon.extract(self, page)


class QueueWhitelist(models.Model):
    url = models.TextField(unique=True)

    def __str__(self):
        return self.url


class UrlQueue(models.Model):
    url = models.TextField(unique=True)
    error = models.TextField(blank=True, default='')
    error_hash = models.TextField(blank=True, default='')
    worker_no = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.url

    def set_error(self, err):
        self.error = err
        if err == '':
            self.error_hash = ''
        else:
            self.error_hash = md5(err.encode('utf-8')).hexdigest()

    @staticmethod
    def queue(url, crawl_id=None):
        if crawl_id:
            try:
                Document.objects.get(url=url, crawl_id=crawl_id)
                return
            except Document.DoesNotExist:
                pass

        for w in QueueWhitelist.objects.all():
            if url.startswith(w.url):
                break
        else:
            return

        UrlQueue.objects.get_or_create(url=url)

    @staticmethod
    def crawl(worker_no, crawl_id):
        url = UrlQueue.pick_url(worker_no)
        if url is None:
            return False

        doc = None
        try:
            print('(%i/%i) %i %s ...' % (UrlQueue.objects.count(), Document.objects.count(), worker_no, url.url))

            doc, _ = Document.objects.get_or_create(url=url.url, defaults={'crawl_id': crawl_id})
            if url.url.startswith('http://') or url.url.startswith('https://'):
                domain_policy = doc.get_policy()
                page = domain_policy.url_get(url.url)
                doc, _ = Document.objects.get_or_create(url=page.url, defaults={'crawl_id': crawl_id})
                doc.normalized_url = page.url.split('://', 1)[0].replace('/', ' ')
                doc.index(page, crawl_id)

            doc.crawl_id = crawl_id
            doc.save()

            UrlQueue.objects.filter(id=url.id).delete()
        except Exception as e:
            if doc:
                doc.delete()
            url.set_error(format_exc())
            url.save()
            print(format_exc())

        worker_stats, created = WorkerStats.objects.get_or_create(defaults={'doc_processed': 0}, worker_no=worker_no)
        worker_stats.doc_processed += 1
        worker_stats.save()
        return True

    @staticmethod
    def pick_url(worker_no):
        while True:
            url = UrlQueue.objects.filter(error='', worker_no__isnull=True).first()
            if url is None:
                return None

            updated = UrlQueue.objects.filter(id=url.id, worker_no__isnull=True).update(worker_no=worker_no)

            if updated == 0:
                sleep(0.1)
                continue

            try:
                url.refresh_from_db()
            except UrlQueue.DoesNotExist:
                sleep(0.1)
                continue

            return url


class AuthMethod(models.Model):
    url_re = models.TextField()
    form_selector = models.TextField()
    cookies = models.TextField(blank=True, default='')
    fqdn = models.CharField(max_length=1024)

    def __str__(self):
        return self.url_re

    @staticmethod
    def get_method(url):
        for auth_method in AuthMethod.objects.all():
            if re.search(auth_method.url_re, url):
                return auth_method

    @staticmethod
    def get_cookies(url):
        url = urlparse(url)
        try:
            cookies = AuthMethod.objects.get(fqdn=url.hostname).cookies
            if cookies:
                return json.loads(cookies)
        except AuthMethod.DoesNotExist:
            pass


class AuthField(models.Model):
    key = models.CharField(max_length=256)
    value = models.CharField(max_length=256)
    auth_method = models.ForeignKey(AuthMethod, on_delete=models.CASCADE)

    def __str__(self):
        return '%s: %s' % (self.key, self.value)


class WorkerStats(models.Model):
    doc_processed = models.PositiveIntegerField()
    worker_no = models.IntegerField()


class CrawlerStats(models.Model):
    MINUTELY = 'M'
    DAILY = 'D'
    FREQUENCY = (
        (MINUTELY, MINUTELY),
        (DAILY, DAILY),
    )

    t = models.DateTimeField()
    doc_count = models.PositiveIntegerField()
    url_queued_count = models.PositiveIntegerField()
    indexing_speed = models.PositiveIntegerField(blank=True, null=True)
    freq = models.CharField(max_length=1, choices=FREQUENCY)

    @staticmethod
    def create_daily():
        CrawlerStats.objects.filter(t__lt=now() - timedelta(days=365), freq=CrawlerStats.MINUTELY).delete()
        last = CrawlerStats.objects.filter(freq=CrawlerStats.DAILY).order_by('t').last()
        today = now().replace(hour=0, minute=0, second=0, microsecond=0)

        if last and last.t == today:
            return

        doc_count = WorkerStats.objects.all().aggregate(s=models.Sum('doc_processed')).get('s', 0) or 0

        indexing_speed = None
        try:
            yesterday = today - timedelta(days=1)
            yesterday_stat = CrawlerStats.objects.get(freq=CrawlerStats.DAILY, t=yesterday)
            indexing_speed = doc_count - yesterday_stat.doc_count
        except CrawlerStats.DoesNotExist:
            pass

        CrawlerStats.objects.create(t=today,
                                    doc_count=doc_count,
                                    url_queued_count=UrlQueue.objects.count(),
                                    indexing_speed=indexing_speed,
                                    freq=CrawlerStats.DAILY)

    @staticmethod
    def create(t, prev_stat):
        CrawlerStats.objects.filter(t__lt=t - timedelta(hours=24), freq=CrawlerStats.MINUTELY).delete()
        doc_count = WorkerStats.objects.all().aggregate(s=models.Sum('doc_processed')).get('s', 0) or 0
        indexing_speed = None
        if prev_stat:
            indexing_speed = doc_count - prev_stat.doc_count
        return CrawlerStats.objects.create(t=t,
                                           doc_count=doc_count,
                                           url_queued_count=UrlQueue.objects.count(),
                                           indexing_speed=indexing_speed,
                                           freq=CrawlerStats.MINUTELY)


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


def browse_mode_default():
    return settings.BROWSING_METHOD


class DomainPolicy(models.Model):
    SELENIUM = 'selenium'
    REQUESTS = 'requests'
    DETECT = 'detect'

    MODE = [
        (SELENIUM, SELENIUM),
        (REQUESTS, REQUESTS),
        (DETECT, DETECT)
    ]

    url = models.TextField(unique=True)
    browse_mode = models.CharField(max_length=10, choices=MODE, default=browse_mode_default)

    def __str__(self):
        return '%s %s' % (self.url, self.browse_mode)

    def _get_browser(self):
        if settings.BROWSING_METHOD == DomainPolicy.SELENIUM:
            return SeleniumBrowser
        if settings.BROWSING_METHOD == DomainPolicy.REQUESTS:
            return RequestBrowser
        if self.browse_mode in (DomainPolicy.SELENIUM, DomainPolicy.DETECT):
            return SeleniumBrowser
        return RequestBrowser

    def url_get(self, url):
        browser = self._get_browser()
        page = browser.get(url)

        if page.got_redirect:
            # The request was redirected, check if we need auth
            try:
                auth_method = AuthMethod.get_method(url)

                if auth_method:
                    new_page = page.browser.try_auth(page, auth_method)

                    if new_page:
                        page = new_page
            except:
                raise Exception('Authentication failed')

        if self.browse_mode == DomainPolicy.DETECT:
            requests_page = RequestBrowser.get(url)

            if len(list(requests_page.get_links())) != len(list(page.get_links())):
                self.browse_mode = DomainPolicy.SELENIUM
            else:
                self.browse_mode = DomainPolicy.REQUESTS
                page = requests_page
            self.save()

        return page
