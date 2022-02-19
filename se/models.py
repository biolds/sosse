import json
import os
import re
import urllib.parse
import unicodedata

from datetime import date, datetime, timedelta
from defusedxml import ElementTree
from hashlib import md5
from time import sleep
from traceback import format_exc
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import connection, models
from django.utils.timezone import now
from langdetect import DetectorFactory, detect


DetectorFactory.seed = 0


def absolutize_url(url, p):
    if re.match('[a-zA-Z]+:', p):
        return p

    url = urlparse(url)

    if p.startswith('/'):
        new_path = p
    else:
        new_path = os.path.dirname(url.path)
        new_path += '/' + p

    url = url._replace(path=new_path, query='', fragment='')
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
    title = models.TextField()
    normalized_title = models.TextField()
    content = models.TextField()
    normalized_content = models.TextField()
    vector = SearchVectorField()
    lang_iso_639_1 = models.CharField(max_length=6, null=True, blank=True)
    vector_lang = RegConfigField(default='simple')

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
    def _get_lang(cls, text):
        lang_iso = detect(text)
        lang_pg = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get('name')
        if lang_pg not in cls.get_supported_langs():
            lang_pg = settings.MYSE_FAIL_OVER_LANG

        return lang_iso, lang_pg

    @classmethod
    def _get_soup(self, content):
        content = content.decode('utf-8')
        parsed = BeautifulSoup(content, 'html5lib')

        # Remove <template> tags as BS extract its text
        for elem in parsed.find_all('template'):
            elem.extract()
        return parsed

    def index(self, content, crawl_id):
        parsed = self._get_soup(content)
        title = parsed.title and parsed.title.string
        self.title = title or self.url
        self.normalized_title = remove_accent(self.title + '\n' + self.url)

        text = ''
        for string in parsed.strings:
            s = string.strip(' \t\n\r')
            if s != '':
                if text != '':
                    text += '\n'
                text += s
        self.content = text
        self.normalized_content = remove_accent(text)

        self.lang_iso_639_1, self.vector_lang = self._get_lang((title or '') + '\n' + text)

        # extract links
        for a in parsed.find_all('a'):
            url = absolutize_url(self.url, a.get('href'))
            UrlQueue.queue(url, crawl_id)

        for meta in parsed.find_all('meta'):
            if meta.get('http-equiv', '').lower() == 'refresh' and meta.get('content', ''):
                # handle redirect
                dest = meta.get('content')

                if ';' in dest:
                    dest = dest.split(';', 1)[1]

                if dest.startswith('url='):
                    dest = dest[4:]

                dest = absolutize_url(self.url, dest)
                UrlQueue.queue(dest, crawl_id)


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
    def url_get(url):
        cookies = AuthMethod.get_cookies(url)
        r = requests.get(url, cookies=cookies)

        if len(r.history):
            # The request was redirected, check if we need auth
            try:
                new_req = AuthMethod.try_methods(r)
                if new_req:
                    r = new_req
            except:
                raise Exception('Authentication failed')

        r.raise_for_status()
        return r

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
                req = UrlQueue.url_get(url.url)
                doc.url = req.url
                doc.index(req.content, crawl_id)

            doc.crawl_id = crawl_id
            doc.save()

            UrlQueue.objects.filter(id=url.id).delete()
        except Exception as e:
            if doc:
                doc.delete()
            url.set_error(format_exc())
            url.save()
            print(format_exc())
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
    post_url = models.TextField()
    cookies = models.TextField(blank=True, default='')
    fqdn = models.CharField(max_length=1024)

    def __str__(self):
        return self.url_re

    def try_auth(self, req):
        payload = dict([(f['key'], f['value']) for f in self.authfield_set.values('key', 'value')])

        for field in self.authdynamicfield_set.all():
            content = req.content.decode('utf-8')
            parsed = BeautifulSoup(content, 'html5lib')
            val = parsed.select(field.input_css_selector)

            if len(val) == 0:
                raise Exception('Could not find element with CSS selector: %s' % field.input_css_selector)

            if len(val) > 1:
                raise Exception('Found multiple element with CSS selector: %s' % field.input_css_selector)

            payload[field.key] = val[0].attrs['value']

        cookies = dict(req.cookies)
        r = requests.post(self.post_url, data=payload, cookies=cookies, allow_redirects=False)
        r.raise_for_status()

        self.cookies = json.dumps(dict(r.cookies))
        self.save()

        if r.status_code != 302:
            return r

        location = r.headers.get('location')
        if not location:
            raise Exception('No location in the redirection')

        location = absolutize_url(req.url, location)
        r = requests.get(req.url, cookies=r.cookies)
        r.raise_for_status()
        return r

    @staticmethod
    def try_methods(req):
        for auth_method in AuthMethod.objects.all():
            if re.search(auth_method.url_re, req.url):
                return auth_method.try_auth(req)

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


class AuthDynamicField(models.Model):
    key = models.CharField(max_length=256)
    input_css_selector = models.CharField(max_length=4096)
    auth_method = models.ForeignKey(AuthMethod, on_delete=models.CASCADE)

    def __str__(self):
        return '%s: %s' % (self.key, self.input_css_selector)


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

        doc_count = Document.objects.count()

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
        doc_count = Document.objects.count()
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
