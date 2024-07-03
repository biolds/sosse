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

import os
import re
import urllib.parse
import logging

from base64 import b64encode, b64decode
from datetime import timedelta
from defusedxml import ElementTree
from hashlib import md5
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction, DataError
from django.http import QueryDict
from django.utils.timezone import now
from publicsuffix2 import get_public_suffix, PublicSuffixList
import requests

from .browser import AuthElemFailed, ChromiumBrowser, FirefoxBrowser, RequestBrowser, TooManyRedirects
from .document import Document
from .online import online_status
from .url import absolutize_url, url_remove_fragment, url_remove_query_string

crawl_logger = logging.getLogger('crawler')


class Link(models.Model):
    doc_from = models.ForeignKey(Document, null=True, blank=True, on_delete=models.SET_NULL, related_name='links_to')
    doc_to = models.ForeignKey(Document, null=True, blank=True, on_delete=models.CASCADE, related_name='linked_from')
    text = models.TextField(null=True, blank=True)
    pos = models.PositiveIntegerField()
    link_no = models.PositiveIntegerField()
    extern_url = models.TextField(null=True, blank=True)
    screen_pos = models.CharField(max_length=64, null=True, blank=True)
    in_nav = models.BooleanField(default=False)

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
                # Debian install
                if arg == b'sosse.sosse_admin' and args[i + 1] == b'crawl':
                    break
                # Pip install
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
    short_name = models.CharField(unique=True, max_length=32, blank=True, default='')
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
    def should_redirect(cls, query, request=None):
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
            if settings.SOSSE_ONLINE_SEARCH_REDIRECT and request and online_status(request) == 'online':
                se = SearchEngine.objects.filter(short_name=settings.SOSSE_ONLINE_SEARCH_REDIRECT).first()

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

        url = absolutize_url(doc.url, url)
        url = url_remove_query_string(url_remove_fragment(url))

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
                page = RequestBrowser.get(url, check_status=True)
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
    BROWSE_CHROMIUM = 'selenium'
    BROWSE_FIREFOX = 'firefox'
    BROWSE_REQUESTS = 'requests'
    BROWSE_MODE = [
        (BROWSE_DETECT, 'Detect'),
        (BROWSE_CHROMIUM, 'Chromium'),
        (BROWSE_FIREFOX, 'Firefox'),
        (BROWSE_REQUESTS, 'Python Requests'),
    ]

    ROBOTS_UNKNOWN = 'unknown'
    ROBOTS_EMPTY = 'empty'
    ROBOTS_LOADED = 'loaded'

    ROBOTS_STATUS = [
        (ROBOTS_UNKNOWN, 'Unknown'),
        (ROBOTS_EMPTY, 'Empty'),
        (ROBOTS_LOADED, 'Loaded')
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
            self._parse_robotstxt(page.content.decode('utf-8'))
        except (requests.HTTPError, TooManyRedirects):
            self.robots_status = DomainSetting.ROBOTS_EMPTY
        else:
            self.robots_status = DomainSetting.ROBOTS_LOADED
        crawl_logger.debug('%s: robots.txt %s' % (self.domain, self.robots_status))

    def robots_authorized(self, url):
        if self.ignore_robots:
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
    DomainSetting.BROWSE_CHROMIUM: ChromiumBrowser,
    DomainSetting.BROWSE_FIREFOX: FirefoxBrowser,
    DomainSetting.BROWSE_REQUESTS: RequestBrowser,
}


@transaction.atomic
def validate_regexp(val):
    cursor = connection.cursor()
    try:
        # Try the regexp on Psql
        cursor.execute('SELECT 1 FROM se_document WHERE url ~ %s', params=[val])
    except DataError as e:
        raise ValidationError(e.__cause__)


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

    REMOVE_NAV_FROM_INDEX = 'idx'
    REMOVE_NAV_FROM_SCREENSHOT = 'scr'
    REMOVE_NAV_FROM_ALL = 'yes'
    REMOVE_NAV_NO = 'no'
    REMOVE_NAV = [
        (REMOVE_NAV_FROM_INDEX, 'From index'),
        (REMOVE_NAV_FROM_SCREENSHOT, 'From index and screenshots'),
        (REMOVE_NAV_FROM_ALL, 'From index, screens and HTML snaps'),
        (REMOVE_NAV_NO, 'No')
    ]

    url_regex = models.TextField(unique=True, validators=[validate_regexp])
    enabled = models.BooleanField(default=True)
    recursion = models.CharField(max_length=6, choices=CRAWL_CONDITION, default=CRAWL_ALL)
    mimetype_regex = models.TextField(default='text/.*')
    recursion_depth = models.PositiveIntegerField(default=0, help_text='Level of external links (links that don\'t match the regex) to recurse into')
    keep_params = models.BooleanField(default=True, verbose_name='Index URL parameters', help_text='When disabled, URL parameters (parameters after "?") are removed from URLs, this can be useful if some parameters are random, change sorting or filtering, ...')
    hide_documents = models.BooleanField(default=False, help_text='Hide documents from search results')

    default_browse_mode = models.CharField(max_length=8, choices=DomainSetting.BROWSE_MODE, default=DomainSetting.BROWSE_CHROMIUM, help_text='Python Request is faster, but can\'t execute Javascript and may break pages')

    snapshot_html = models.BooleanField(default=True, help_text='Store pages as HTML and download requisite assets', verbose_name='Snapshot HTML 🔖')
    snapshot_exclude_url_re = models.TextField(blank=True, default='', help_text='Regexp of URL to skip asset downloading')
    snapshot_exclude_mime_re = models.TextField(blank=True, default='', help_text='Regexp of mimetypes to skip asset saving')
    snapshot_exclude_element_re = models.TextField(blank=True, default='', help_text='Regexp of elements to skip asset downloading')

    create_thumbnails = models.BooleanField(default=True, help_text='Create thumbnails to display in search results')
    take_screenshots = models.BooleanField(default=False, help_text='Store pages as screenshots', verbose_name='Take screenshots 📷')
    screenshot_format = models.CharField(max_length=3, choices=Document.SCREENSHOT_FORMAT, default=Document.SCREENSHOT_JPG)

    remove_nav_elements = models.CharField(default=REMOVE_NAV_FROM_INDEX, help_text='Remove navigation related elements', choices=REMOVE_NAV, max_length=4)
    script = models.TextField(default='', help_text='Javascript code to execute after the page is loaded', blank=True)
    store_extern_links = models.BooleanField(default=False, help_text='Store links to non-indexed pages')

    recrawl_mode = models.CharField(max_length=8, choices=RECRAWL_MODE, default=RECRAWL_ADAPTIVE, verbose_name='Crawl frequency', help_text='Adaptive frequency will increase delay between two crawls when the page stays unchanged')
    recrawl_dt_min = models.DurationField(blank=True, null=True, help_text='Min. time before recrawling a page', default=timedelta(days=1))
    recrawl_dt_max = models.DurationField(blank=True, null=True, help_text='Max. time before recrawling a page', default=timedelta(days=365))
    hash_mode = models.CharField(max_length=10, choices=HASH_MODE, default=HASH_NO_NUMBERS, help_text='Page content hashing method used to detect changes in the content')

    auth_login_url_re = models.TextField(null=True, blank=True, verbose_name='Login URL regexp', help_text='A redirection to an URL matching the regexp will trigger authentication')
    auth_form_selector = models.TextField(null=True, blank=True, verbose_name='Form selector', help_text='CSS selector pointing to the authentication &lt;form&gt; element')

    class Meta:
        verbose_name_plural = 'crawl policies'

    def __str__(self):
        return f'「{self.url_regex}」'

    def save(self, *args, **kwargs):
        if self.url_regex == '.*':
            self.enabled = True
        return super().save(*args, **kwargs)

    @staticmethod
    def create_default():
        # mandatory default policy
        policy, _ = CrawlPolicy.objects.get_or_create(url_regex='.*')
        return policy

    @staticmethod
    def get_from_url(url, queryset=None):
        if queryset is None:
            queryset = CrawlPolicy.objects.all()
        queryset = queryset.filter(enabled=True)

        policy = queryset.extra(where=['%s ~ url_regex'], params=[url]).annotate(
            url_regex_len=models.functions.Length('url_regex')
        ).order_by('-url_regex_len').first()

        if policy is None:
            return CrawlPolicy.create_default()
        return policy

    @staticmethod
    def _default_browser():
        if settings.SOSSE_DEFAULT_BROWSER == 'chromium':
            return DomainSetting.BROWSE_CHROMIUM
        return DomainSetting.BROWSE_FIREFOX

    def url_get(self, url, domain_setting=None):
        domain_setting = domain_setting or DomainSetting.get_from_url(url, self.default_browse_mode)
        browser = self.get_browser(domain_setting=domain_setting, no_detection=False)
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
            browser_content = page.dom_walk(self, False, None)
            requests_content = requests_page.dom_walk(self, False, None)

            if browser_content['text'] != requests_content['text']:
                new_mode = self._default_browser()
            else:
                new_mode = DomainSetting.BROWSE_REQUESTS
                page = requests_page
            crawl_logger.debug('browser detected %s on %s' % (new_mode, url))
            domain_setting.browse_mode = new_mode
            domain_setting.save()
        return page

    def get_browser(self, url=None, domain_setting=None, no_detection=True):
        if url is None and domain_setting is None:
            raise Exception('Either url or domain_setting must be provided')
        if url is not None and domain_setting is not None:
            raise Exception('Either url or domain_setting must be provided')

        if url:
            domain_setting = DomainSetting.get_from_url(url, self.default_browse_mode)

        browser_str = self.default_browse_mode
        if self.default_browse_mode == DomainSetting.BROWSE_DETECT:
            if domain_setting.browse_mode == DomainSetting.BROWSE_DETECT:
                if no_detection:
                    raise Exception('browser mode is not yet known (%s)' % domain_setting)
                browser_str = self._default_browser()
            else:
                browser_str = domain_setting.browse_mode
        return BROWSER_MAP[browser_str]


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
    starting_with = models.BooleanField(default=False, help_text='Exclude all urls starting with the url pattern')
    comment = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Excluded URL'
