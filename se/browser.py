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

import json
import logging
import os
import pytz
import psutil
import shlex
import traceback
from datetime import datetime
from time import sleep
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment, Doctype, Tag
from django.conf import settings
from PIL import Image
import requests
import selenium
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromiumOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from urllib3.exceptions import HTTPError

from .url import absolutize_url, has_browsable_scheme, sanitize_url, url_remove_fragment, url_remove_query_string
from .utils import human_filesize

crawl_logger = logging.getLogger('crawler')

NAV_ELEMENTS = ['nav', 'header', 'footer']


def dict_merge(a, b):
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            dict_merge(a[key], b[key])
        else:
            a[key] = b[key]
    return a


class AuthElemFailed(Exception):
    def __init__(self, page, *args, **kwargs):
        self.page = page
        super().__init__(*args, **kwargs)


class SkipIndexing(Exception):
    pass


class StalledDownload(SkipIndexing):
    def __init__(self):
        super().__init__('Download stalled')


class PageTooBig(SkipIndexing):
    def __init__(self, size, conf_size):
        size = human_filesize(size)
        conf_size = human_filesize(conf_size * 1024)
        super().__init__(f'Document size is too big ({size} > {conf_size}). You can increase the `max_file_size` and `max_html_asset_size` option in the configuration to index this file.')


class TooManyRedirects(SkipIndexing):
    def __init__(self):
        super().__init__(f'Max redirects ({settings.SOSSE_MAX_REDIRECTS}) reached. You can increase the `max_redirects` option in the configuration file in case it\'s needed.')


class Page:
    def __init__(self, url, content, browser, mimetype=None, headers=None, status_code=None):
        assert isinstance(content, bytes)
        self.url = sanitize_url(url)
        self.content = content
        self.redirect_count = 0
        self.title = None
        self.soup = None
        self.browser = browser
        self.mimetype = mimetype
        self.headers = headers or {}
        self.status_code = status_code

    def get_soup(self):
        if self.soup:
            return self.soup
        content = self.content.decode('utf-8', errors='replace')
        self.soup = BeautifulSoup(content, 'html5lib')

        # Remove <template> tags as BS extract its text
        for elem in self.soup.find_all('template'):
            elem.extract()
        return self.soup

    def get_links(self, keep_params):
        for a in self.get_soup().find_all('a'):
            if a.get('href'):
                url = absolutize_url(self.url, a.get('href').strip())
                if not keep_params:
                    url = url_remove_query_string(url)
                url = url_remove_fragment(url)
                yield url

    def update_soup(self, soup):
        self.soup = soup

    def dump_html(self):
        return self.get_soup().encode()

    def base_url(self):
        soup = self.get_soup()

        base_url = self.url
        if soup.head.base and soup.head.base.get('href'):
            base_url = absolutize_url(self.url, soup.head.base.get('href'))
            base_url = url_remove_fragment(base_url)
        return base_url

    def remove_nav_elements(self):
        soup = self.get_soup()
        for elem_type in NAV_ELEMENTS:
            for elem in soup.find_all(elem_type):
                elem.extract()

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

    def _build_selector(self, elem):
        no = 1
        for sibling in elem.previous_siblings:
            if isinstance(elem, Tag) and sibling.name == elem.name:
                no += 1

        selector = '/%s[%i]' % (elem.name, no)

        if elem.name != 'html':
            selector = self._build_selector(elem.parent) + selector
        return selector

    def _dom_walk(self, elem, crawl_policy, links, queue_links, document, in_nav=False):
        assert queue_links == (document is not None), 'document parameter (%s) is required to queue links (%s)' % (document, queue_links)
        from .models import CrawlPolicy, Document, Link
        if isinstance(elem, (Doctype, Comment)):
            return

        if elem.name in ('[document]', 'title', 'script', 'style'):
            return

        if crawl_policy.remove_nav_elements != CrawlPolicy.REMOVE_NAV_NO and elem.name in ('nav', 'header', 'footer'):
            in_nav = True

        s = self._get_elem_text(elem)

        # Keep the link if it has text, or if we take screenshots
        if elem.name in (None, 'a'):
            if links['text'] and links['text'][-1] not in (' ', '\n') and s and not in_nav:
                links['text'] += ' '

            if elem.name == 'a' and queue_links:
                href = elem.get('href')
                if href:
                    link = None
                    target_doc = None
                    href = href.strip()

                    if has_browsable_scheme(href):
                        href_for_policy = absolutize_url(self.base_url(), href)
                        child_policy = CrawlPolicy.get_from_url(href_for_policy)
                        href = absolutize_url(self.base_url(), href)
                        if not child_policy.keep_params:
                            href = url_remove_query_string(href)
                        href = url_remove_fragment(href)
                        target_doc = Document.queue(href, crawl_policy, document)

                        if target_doc != document:
                            if target_doc:
                                link = Link(doc_from=document,
                                            link_no=len(links['links']),
                                            doc_to=target_doc,
                                            text=s,
                                            pos=len(links['text']),
                                            in_nav=in_nav)

                    store_extern_link = (not has_browsable_scheme(href) or target_doc is None)
                    if crawl_policy.store_extern_links and store_extern_link:
                        href = elem.get('href').strip()
                        try:
                            href = absolutize_url(self.base_url(), href)
                        except ValueError:
                            # Store the url as is if it's invalid
                            pass
                        link = Link(doc_from=document,
                                    link_no=len(links['links']),
                                    text=s,
                                    pos=len(links['text']),
                                    extern_url=href,
                                    in_nav=in_nav)

                    if link:
                        if crawl_policy.take_screenshots:
                            link.css_selector = self._build_selector(elem)
                        links['links'].append(link)

            if s and not in_nav:
                links['text'] += s

            if elem.name == 'a':
                return

        if hasattr(elem, 'children'):
            for child in elem.children:
                self._dom_walk(child, crawl_policy, links, queue_links, document, in_nav)

        if elem.name in ('div', 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            if links['text'] and not in_nav:
                if links['text'][-1] == ' ':
                    links['text'] = links['text'][:-1] + '\n'
                elif links['text'][-1] != '\n':
                    links['text'] += '\n'

    def dom_walk(self, crawl_policy, queue_links, document):
        links = {
            'links': [],
            'text': ''
        }
        for elem in self.get_soup().children:
            self._dom_walk(elem, crawl_policy, links, queue_links, document, False)
        return links


class Browser:
    inited = False

    @classmethod
    def init(cls):
        if cls.inited:
            return
        crawl_logger.debug('Browser %s init' % cls.__name__)
        cls._init()
        cls.inited = True

    @classmethod
    def destroy(cls):
        if not cls.inited:
            return
        crawl_logger.debug('Browser %s destroy' % cls.__name__)
        cls._destroy()
        cls.inited = False

    @classmethod
    def _init(cls):
        raise NotImplementedError()

    @classmethod
    def _destroy(cls):
        raise NotImplementedError()


class RequestBrowser(Browser):
    @classmethod
    def _init(cls):
        pass

    @classmethod
    def _destroy(cls):
        pass

    @classmethod
    def _page_from_request(cls, r):
        content = r._content
        mimetype = r.headers.get('content-type') or 'application/octet-stream'
        if ';' in mimetype:
            mimetype, _ = mimetype.split(';', 1)

        page = Page(r.url, content, cls, mimetype, r.headers, r.status_code)
        soup = page.get_soup()
        if soup:
            page.title = soup.title and soup.title.string
        return page

    @classmethod
    def _set_cookies(cls, url, cookies):
        from .models import Cookie
        _cookies = []

        for cookie in cookies:
            expires = cookie.expires
            if expires:
                expires = datetime.fromtimestamp(expires, pytz.utc)

            c = {
                'domain': cookie.get_nonstandard_attr('Domain'),
                'name': cookie.name,
                'value': cookie.value,
                'path': cookie.path,
                'expires': expires,
                'secure': cookie.secure,
                'same_site': cookie.get_nonstandard_attr('SameSite'),
                'http_only': cookie.has_nonstandard_attr('HttpOnly')
            }
            _cookies.append(c)

        Cookie.set(url, _cookies)

    @classmethod
    def _get_cookies(cls, url):
        from .models import Cookie
        jar = requests.cookies.RequestsCookieJar()

        for c in Cookie.get_from_url(url):
            expires = None
            if c.expires:
                expires = int(c.expires.strftime('%s'))

            rest = {'SameSite': c.same_site}
            if c.http_only:
                rest['HttpOnly'] = c.http_only,
            jar.set(c.name, c.value, path=c.path, domain=c.domain, expires=expires, secure=c.secure, rest=rest)
        crawl_logger.debug('loading cookies for %s: %s', url, jar)
        return jar

    @classmethod
    def _requests_params(cls):
        params = {
            'stream': True,
            'allow_redirects': False,
            'headers': {
                'User-Agent': settings.SOSSE_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        }

        if settings.SOSSE_PROXY:
            params['proxies'] = {
                'http': settings.SOSSE_PROXY,
                'https': settings.SOSSE_PROXY
            }
        if settings.SOSSE_REQUESTS_TIMEOUT:
            params['timeout'] = settings.SOSSE_REQUESTS_TIMEOUT
        return params

    @classmethod
    def _requests_query(cls, method, url, max_file_size, **kwargs):
        jar = cls._get_cookies(url)
        crawl_logger.debug('from the jar: %s', jar)
        s = requests.Session()
        s.cookies = jar

        func = getattr(s, method)
        kwargs = dict_merge(cls._requests_params(), kwargs)
        r = func(url, **kwargs)
        cls._set_cookies(url, s.cookies)

        content_length = int(r.headers.get('content-length', 0))
        if content_length / 1024 > max_file_size:
            r.close()
            raise PageTooBig(content_length, max_file_size)

        content = b''
        for chunk in r.iter_content(chunk_size=1024):
            content += chunk
            if len(content) / 1024 >= max_file_size:
                break
        r.close()

        if len(content) / 1024 > max_file_size:
            raise PageTooBig(len(content), max_file_size)

        r._content = content
        crawl_logger.debug('after request jar: %s', s.cookies)
        return r

    @classmethod
    def get(cls, url, check_status=False, max_file_size=settings.SOSSE_MAX_FILE_SIZE, **kwargs):
        REDIRECT_CODE = (301, 302, 307, 308)
        page = None
        redirect_count = 0

        while redirect_count <= settings.SOSSE_MAX_REDIRECTS:
            r = cls._requests_query('get', url, max_file_size, **kwargs)

            if check_status:
                r.raise_for_status()

            if r.status_code in REDIRECT_CODE:
                crawl_logger.debug('%s: redirected' % url)
                redirect_count += 1
                dest = r.headers.get('location')
                url = absolutize_url(url, dest)
                url = url_remove_fragment(url)
                crawl_logger.debug('got redirected to %s' % url)
                if not url:
                    raise Exception('Got a %s code without a location header' % r.status_code)

                continue

            page = cls._page_from_request(r)

            # Check for an HTML / meta redirect
            soup = page.get_soup()
            if soup:
                for meta in page.get_soup().find_all('meta'):
                    if meta.get('http-equiv', '').lower() == 'refresh' and meta.get('content', ''):
                        # handle redirect
                        dest = meta.get('content')

                        if ';' in dest:
                            dest = dest.split(';', 1)[1]

                        if dest.startswith('url='):
                            dest = dest[4:]

                        url = absolutize_url(url, dest)
                        url = url_remove_fragment(url)
                        redirect_count += 1
                        crawl_logger.debug('%s: html redirected' % url)
                        continue
            break

        if redirect_count > settings.SOSSE_MAX_REDIRECTS:
            raise TooManyRedirects()

        page.redirect_count = redirect_count
        return page

    @classmethod
    def try_auth(cls, page, url, crawl_policy):
        parsed = page.get_soup()
        form = parsed.select(crawl_policy.auth_form_selector)

        if len(form) == 0:
            raise AuthElemFailed(page, 'Could not find element with CSS selector: %s' % crawl_policy.auth_form_selector)

        if len(form) > 1:
            raise AuthElemFailed(page, 'Found multiple element with CSS selector: %s' % crawl_policy.auth_form_selector)

        form = form[0]
        payload = {}
        for elem in form.find_all('input'):
            if elem.get('name'):
                payload[elem.get('name')] = elem.get('value')

        for f in crawl_policy.authfield_set.values('key', 'value'):
            payload[f['key']] = f['value']

        post_url = form.get('action')
        if post_url:
            post_url = absolutize_url(page.url, post_url)
            post_url = url_remove_fragment(post_url)
        else:
            post_url = page.url

        crawl_logger.debug('authenticating to %s with %s', post_url, payload)
        r = cls._requests_query('post', post_url, settings.SOSSE_MAX_FILE_SIZE, data=payload)
        if r.status_code != 302:
            crawl_logger.debug('no redirect after auth')
            return cls._page_from_request(r)

        location = r.headers.get('location')
        if not location:
            raise Exception('No location in the redirection')

        location = absolutize_url(r.url, location)
        location = url_remove_fragment(location)
        crawl_logger.debug('got redirected to %s after authentication' % location)
        return cls.get(location)


def retry(f):
    def _retry(*args, **kwargs):
        count = 0
        while count <= settings.SOSSE_BROWSER_CRASH_RETRY:
            try:
                r = f(*args, **kwargs)
                crawl_logger.debug('%s succeeded' % f)
                return r
            except (WebDriverException, HTTPError):
                exc = traceback.format_exc()
                crawl_logger.error('%s failed' % f)
                crawl_logger.error('Selenium returned an exception:\n%s' % exc)

                cls = args[0]
                cls.destroy()
                sleep(settings.SOSSE_BROWSER_CRASH_SLEEP)
                cls.init()

                if count == settings.SOSSE_BROWSER_CRASH_RETRY:
                    raise
                count += 1
                crawl_logger.error('Retrying (%i / %i)' % (count, settings.SOSSE_BROWSER_CRASH_RETRY))
    return _retry


class SeleniumBrowser(Browser):
    _worker_no = 0
    _driver = None
    cookie_loaded = []
    COOKIE_LOADED_SIZE = 1024
    first_init = True

    @classmethod
    @property
    def driver(cls):
        cls.init()
        return cls._driver

    @classmethod
    def _init(cls):
        if not os.path.isdir(ChromiumBrowser._get_download_dir()):
            os.makedirs(ChromiumBrowser._get_download_dir())
        if not os.path.isdir(FirefoxBrowser._get_download_dir()):
            os.makedirs(FirefoxBrowser._get_download_dir())

        # force the cwd in case it's not called from the worker
        if not os.getcwd().startswith(settings.SOSSE_TMP_DL_DIR + '/'):
            # change cwd to Chromium's because it downloads directory (while Firefox has an option for target dir)
            os.chdir(ChromiumBrowser._get_download_dir())

        # Force HOME directory as it used for Firefox profile loading
        os.environ['HOME'] = '/var/www'

        config_dir = settings.SOSSE_BROWSER_CONFIG_DIR
        os.environ['XDG_CONFIG_HOME'] = config_dir

        opt_key = 'SOSSE_%s_OPTIONS' % cls.name.upper()
        opts = shlex.split(getattr(settings, opt_key))
        opts.append('--window-size=%s,%s' % cls.screen_size())
        opts += cls._get_options()

        has_incognito = False
        options = cls._get_options_obj()
        for opt in opts:
            if cls.first_init:
                crawl_logger.info('Passing option %s', opt)
            options.add_argument(opt)

            if '--incognito' in opt:
                has_incognito = True

        if cls.first_init and has_incognito:
            crawl_logger.warning('Passing --incognito breaks file downloads on some versions of Chromium')

        cls.first_init = False
        cls._driver = cls._get_driver(options)
        cls._driver.delete_all_cookies()

    @classmethod
    def _destroy(cls):
        if cls._driver:
            # Ignore errors in case the browser crashed
            try:
                cls._driver.close()
            except:  # noqa
                pass

            try:
                cls._driver.quit()
            except:  # noqa
                pass

    @classmethod
    def _current_url(cls):
        if cls.driver.current_url.startswith('data:'):
            return ''
        return sanitize_url(cls.driver.current_url)

    @classmethod
    def _driver_get(cls, url):
        raise NotImplementedError()

    @classmethod
    def _wait_for_ready(cls, url):
        crawl_logger.debug('wait_for_ready %s, %s / %s / %s', url, settings.SOSSE_MAX_REDIRECTS, settings.SOSSE_JS_STABLE_RETRY, settings.SOSSE_JS_STABLE_TIME)
        redirect_count = 0

        while redirect_count <= settings.SOSSE_MAX_REDIRECTS:
            # Wait for page being ready
            retry = settings.SOSSE_JS_STABLE_RETRY
            while retry > 0 and cls._current_url() == url:
                retry -= 1
                if cls.driver.execute_script('return document.readyState === "complete";'):
                    break
                sleep(settings.SOSSE_JS_STABLE_TIME)

            new_url = cls._current_url()
            if new_url != url:
                crawl_logger.debug('detected redirect %i %s -> %s', redirect_count, url, new_url)
                redirect_count += 1
                url = new_url
                continue

            crawl_logger.debug('js stabilization start %s', url)
            # Wait for page content to be stable
            retry = settings.SOSSE_JS_STABLE_RETRY
            previous_content = None
            content = None

            while retry > 0 and cls._current_url() == url:
                retry -= 1
                content = cls.driver.page_source

                if content == previous_content:
                    break
                previous_content = content
                sleep(settings.SOSSE_JS_STABLE_TIME)
                crawl_logger.debug('js changed %s', url)

            if cls._current_url() != url:
                redirect_count += 1
                url = cls._current_url()
                continue
            else:
                crawl_logger.debug('js stable %s', url)
                break

        if redirect_count > settings.SOSSE_MAX_REDIRECTS:
            raise TooManyRedirects()

        return redirect_count

    @classmethod
    def remove_nav_elements(cls):
        cls.driver.execute_script('''
        const tags = %s;
        tags.map((tag) => {
            const elems = document.getElementsByTagName(tag);
            for (no = 0; no < elems.length; no++) {
                elems[no].remove();
            }
        });
        ''' % json.dumps(NAV_ELEMENTS))

    @classmethod
    def _get_page(cls, url):
        from .models import CrawlPolicy
        redirect_count = cls._wait_for_ready(url)

        current_url = cls.driver.current_url
        crawl_policy = CrawlPolicy.get_from_url(current_url)
        if crawl_policy and crawl_policy.script:
            cls.driver.execute_script(crawl_policy.script)
            cls._wait_for_ready(url)

        content = cls.driver.page_source.encode('utf-8')
        page = Page(current_url,
                    content,
                    cls)
        page.title = cls.driver.title
        page.redirect_count = redirect_count
        return page

    @classmethod
    def _save_cookies(cls, url):
        from .models import Cookie
        _cookies = []
        crawl_logger.debug('got cookies %s' % cls.driver.get_cookies())
        for cookie in cls.driver.get_cookies():
            c = {
                'name': cookie['name'],
                'value': cookie['value'],
                'path': cookie['path'],
                'secure': cookie['secure'],
            }

            expires = cookie.get('expiry')
            if expires:
                c['expires'] = datetime.fromtimestamp(expires, pytz.utc)

            if cookie.get('sameSite'):
                c['same_site'] = cookie['sameSite']

            if cookie.get('httpOnly'):
                c['http_only'] = cookie['httpOnly']

            if cookie.get('domain'):
                c['domain'] = cookie['domain']

            _cookies.append(c)

        Cookie.set(url, _cookies)

    @classmethod
    def _load_cookies(cls, url):
        from .models import Cookie

        if not has_browsable_scheme(url):
            return

        # Cookies can only be set to the same domain,
        # so first we navigate to the correct location
        current_url = urlparse(cls._current_url())
        dest = sanitize_url(url)
        target_url = urlparse(dest)
        cookies = Cookie.get_from_url(dest)
        if len(cookies) == 0:
            crawl_logger.debug('no cookie to load for %s' % dest)
            return

        if current_url.netloc != target_url.netloc:
            crawl_logger.debug('navigate for cookie to %s' % dest)
            cls._driver_get(dest)
            cls._wait_for_ready(dest)
            crawl_logger.debug('navigate for cookie done %s' % cls._current_url())

        current_url = cls._current_url()
        if urlparse(current_url).netloc != target_url.netloc:
            # if the browser is initially on about:blank,
            # and then loads a download url, it'll stay on about:blank
            # which does not accept cookie loading
            crawl_logger.debug('could not go to %s to load cookies, nav is stuck on %s (%s)', target_url.netloc, current_url, cls.driver.current_url)
            return

        crawl_logger.debug('clearing cookies')
        cls.driver.delete_all_cookies()
        for c in cookies:
            cookie = {
                'name': c.name,
                'value': c.value,
                'path': c.path,
                'secure': c.secure,
                'sameSite': c.same_site.title(),
            }
            if c.domain_cc:
                cookie['domain'] = c.domain_cc
            if c.expires:
                cookie['expiry'] = int(c.expires.strftime('%s'))
            if c.http_only:
                cookie['httpOnly'] = c.http_only
            try:
                cls.driver.add_cookie(cookie)
                crawl_logger.debug('loaded cookie %s' % cookie)
            except:  # noqa
                raise Exception('%s\n%s' % (cookie, cls.driver.current_url))

    @classmethod
    @retry
    def get(cls, url):
        current_url = cls.driver.current_url
        crawl_logger.debug('get on %s, current %s', url, current_url)

        # Clear the download dir
        crawl_logger.debug('clearing %s' % cls._get_download_dir())
        for f in os.listdir(cls._get_download_dir()):
            f = os.path.join(cls._get_download_dir(), f)
            if os.path.isfile(f):
                crawl_logger.warning('Deleting stale download file %s (you may fix the issue by adjusting "dl_check_*" variables in the conf)' % f)
                os.unlink(f)

        crawl_logger.debug('loading cookies')
        cls._load_cookies(url)
        crawl_logger.debug('driver get')
        cls._driver_get(url)

        if ((current_url != url and cls.driver.current_url == current_url)  # If we got redirected to the url that was previously set in the browser
                or cls.driver.current_url == 'data:,'):  # The url can be "data:," during a few milliseconds when the download starts
            crawl_logger.debug('download starting (%s)', cls.driver.current_url)
            page = cls._handle_download(url)
            if page:
                return page

        crawl_logger.debug('page get')
        page = cls._get_page(url)
        crawl_logger.debug('save cookies')
        cls._save_cookies(url)
        return page

    @classmethod
    def _handle_download(cls, url):
        retry = settings.SOSSE_DL_CHECK_RETRY
        filename = None
        while retry:
            filename = cls._get_download_file()
            if filename is not None:
                try:
                    if os.stat(filename).st_size != 0:
                        # Firefox first create an empty file, then renames it to download into it
                        break
                except FileNotFoundError:
                    sleep(settings.SOSSE_DL_CHECK_TIME)
                    retry -= 1
                    continue

            crawl_logger.debug('no download in progress (%s)', filename)
            sleep(settings.SOSSE_DL_CHECK_TIME)
            retry -= 1
        else:
            # redo the check in case SOSSE_DL_CHECK_RETRY == 0
            filename = cls._get_download_file()

        if filename is None:
            crawl_logger.debug('no download has started on %s', url)
            return

        crawl_logger.debug('Download in progress: %s' % os.listdir(cls._get_download_dir()))
        crawl_logger.debug('Download file: %s' % filename)
        try:
            _size = None
            retry = settings.SOSSE_DL_CHECK_RETRY
            while True:
                sleep(settings.SOSSE_DL_CHECK_TIME)
                size = os.stat(filename).st_size
                if _size == size:
                    retry -= 1
                    if retry <= 0:
                        raise StalledDownload()
                else:
                    retry = settings.SOSSE_DL_CHECK_RETRY

                if size / 1024 > settings.SOSSE_MAX_FILE_SIZE:
                    cls.destroy()  # cancel the download
                    raise PageTooBig(size, settings.SOSSE_MAX_FILE_SIZE)

                if not cls._download_in_progress(filename):
                    break
        except FileNotFoundError:
            # when the download is finished the file is renamed
            pass

        crawl_logger.debug('Download done: %s' % os.listdir(cls._get_download_dir()))

        filename = cls._get_download_file()
        size = os.stat(filename).st_size
        if size / 1024 > settings.SOSSE_MAX_FILE_SIZE:
            raise PageTooBig(size, settings.SOSSE_MAX_FILE_SIZE)
        with open(filename, 'rb') as f:
            content = f.read()

        page = Page(url, content, cls)

        # Remove all files in case multiple were downloaded
        for f in os.listdir(cls._get_download_dir()):
            f = os.path.join(cls._get_download_dir(), f)
            if os.path.isfile(f):
                os.unlink(f)
        return page

    @classmethod
    def screen_size(cls):
        w, h = settings.SOSSE_SCREENSHOTS_SIZE.split('x')
        return int(w), int(h)

    @classmethod
    @retry
    def create_thumbnail(cls, url, image_name):
        width, height = cls.screen_size()
        cls.driver.set_window_rect(0, 0, *cls.screen_size())
        cls.driver.execute_script('document.body.style.overflow = "hidden"')

        base_name = os.path.join(settings.SOSSE_THUMBNAILS_DIR, image_name)
        dir_name = os.path.dirname(base_name)
        os.makedirs(dir_name, exist_ok=True)
        thumb_png = base_name + '.png'
        thumb_jpg = base_name + '.jpg'

        try:
            cls.driver.get_screenshot_as_file(thumb_png)
            with Image.open(thumb_png) as img:
                img = img.convert('RGB')  # Remove alpha channel from the png
                img.thumbnail((160, 100))
                img.save(thumb_jpg, 'jpeg')
        finally:
            if os.path.exists(thumb_png):
                os.unlink(thumb_png)

    @classmethod
    @retry
    def take_screenshots(cls, url, image_name):
        from .models import CrawlPolicy
        crawl_policy = CrawlPolicy.get_from_url(url)
        if crawl_policy and crawl_policy.remove_nav_elements in (CrawlPolicy.REMOVE_NAV_FROM_SCREENSHOT, CrawlPolicy.REMOVE_NAV_FROM_ALL):
            cls.remove_nav_elements()

        base_name = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, image_name)
        dir_name = os.path.dirname(base_name)
        os.makedirs(dir_name, exist_ok=True)

        width, height = cls.screen_size()
        cls.driver.set_window_rect(0, 0, *cls.screen_size())
        cls.driver.execute_script('document.body.style.overflow = "hidden"')
        doc_height = cls.driver.execute_script('''
            const body = document.body;
            const html = document.documentElement;
            return height = Math.max(body.scrollHeight, body.offsetHeight,
                                   html.clientHeight, html.scrollHeight, html.offsetHeight);
        ''')

        crawl_logger.debug('doc_height %s, height %s', doc_height, height)
        img_no = 0
        while (img_no + 1) * height < doc_height:
            cls.scroll_to_page(img_no)
            cls.driver.get_screenshot_as_file('%s_%s.png' % (base_name, img_no))
            img_no += 1

        remaining = doc_height - (img_no * height)
        if remaining > 0:
            cls.driver.set_window_rect(0, 0, width, remaining)
            cls.scroll_to_page(img_no)
            cls.driver.get_screenshot_as_file('%s_%s.png' % (base_name, img_no))
            img_no += 1

        return img_no

    @classmethod
    def scroll_to_page(cls, page_no):
        _, height = cls.screen_size()
        height *= page_no
        cls.driver.execute_script('''
            window.scroll(0, %s);
            [...document.querySelectorAll('*')].filter(x => x.clientHeight < x.scrollHeight).forEach(e => {
                e.scroll({left: 0, top: %s, behavior: 'instant'});
            });
        ''' % (height, height))

    @classmethod
    def get_link_pos_abs(cls, selector):
        return cls.driver.execute_script('''
            const e = document.evaluate('%s', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

            if (e === null) {
                return {}
            };
            let el = e.singleNodeValue;
            if (el === null) {
                return {}
            };
            if (el.children.length === 1 && el.children[0].tagName === 'IMG') {
                el = el.children[0];
            }
            const bodyRect = document.body.getBoundingClientRect();
            const elemRect = el.getBoundingClientRect();
            const pageWidth = %s;
            if (elemRect.left >= pageWidth) {
                return {};
            }
            return {
                elemLeft: elemRect.left,
                elemTop: elemRect.top,
                elemRight: Math.min(pageWidth, elemRect.right),
                elemBottom: elemRect.bottom,
            }
        ''' % (selector, cls.screen_size()[0]))

    @classmethod
    def _find_elements_by_selector(cls, obj, selector):
        if hasattr(obj, 'find_elements_by_css_selector'):
            return obj.find_elements_by_css_selector(selector)

        # Selenium 4
        from selenium.webdriver.common.by import By
        return obj.find_elements(By.CSS_SELECTOR, selector)

    @classmethod
    @retry
    def try_auth(cls, page, url, crawl_policy):
        form = cls._find_elements_by_selector(cls.driver, crawl_policy.auth_form_selector)

        if len(form) == 0:
            raise AuthElemFailed(page, 'Could not find auth element with CSS selector: %s' % crawl_policy.auth_form_selector)

        if len(form) > 1:
            raise AuthElemFailed(page, 'Found multiple auth element with CSS selector: %s' % crawl_policy.auth_form_selector)

        crawl_logger.debug('form found')
        form = form[0]
        for f in crawl_policy.authfield_set.values('key', 'value'):
            elem = cls._find_elements_by_selector(form, 'input[name="%s"]' % f['key'])
            if len(elem) != 1:
                raise Exception('Found %s input element when trying to set auth field %s' % (len(elem), f['key']))
            elem[0].send_keys(f['value'])
            crawl_logger.debug('settings %s = %s on %s' % (f['key'], f['value'], elem[0]))

        dl_dir_files = cls.page_change_wait_setup()
        form.submit()
        crawl_logger.debug('submitting')
        cls.page_change_wait(dl_dir_files)

        current_url = cls._current_url()
        crawl_logger.debug('ready after submit %s', current_url)
        cls._save_cookies(current_url)

        if current_url != url:
            return cls.get(url)

        return cls._get_page(url)

    @classmethod
    def page_change_wait_setup(cls):
        dl_dir_files = sorted(os.listdir(cls._get_download_dir()))
        crawl_logger.debug('dl_dir state: %s', dl_dir_files)

        # Work-around to https://github.com/SeleniumHQ/selenium/issues/4769
        # When a download starts, the regular cls.driver.get call is stuck
        cls.driver.execute_script('''
            window.sosseUrlChanging = true;
            addEventListener('readystatechange', () => {
                window.sosseUrlChanging = false;
            });
        ''')
        return dl_dir_files

    @classmethod
    def page_change_wait(cls, dl_dir_files):
        retry = settings.SOSSE_JS_STABLE_RETRY
        while (cls.driver.current_url == 'about:blank' or cls.driver.execute_script('return window.sosseUrlChanging')) and retry > 0:
            crawl_logger.debug('driver get not done: %s' % cls.driver.current_url)
            if dl_dir_files != sorted(os.listdir(cls._get_download_dir())):
                return
            sleep(settings.SOSSE_JS_STABLE_TIME)
            retry -= 1

    @classmethod
    def _download_in_progress(cls, filename):
        gecko_pid = cls._driver.service.process.pid
        p = psutil.Process(gecko_pid)
        pid = p.children()[0].pid
        fd_dir = '/proc/%d/fd/' % pid

        for f in os.listdir(fd_dir):
            f = os.path.join(fd_dir, f)
            try:
                if os.readlink(f) == filename:
                    return True
            except FileNotFoundError:
                pass
        return False


class ChromiumBrowser(SeleniumBrowser):
    DRIVER_CLASS = webdriver.Chrome
    name = 'chromium'

    @classmethod
    def _get_options_obj(cls):
        options = ChromiumOptions()
        options.binary_location = '/usr/bin/chromium'
        prefs = {
            'profile.default_content_settings.popups': 0,
            'download.default_directory': cls._get_download_dir(),
            'download.prompt_for_download': False,
            'download.directory_upgrade': True
        }
        options.add_experimental_option("prefs", prefs)
        return options

    @classmethod
    def _get_options(cls):
        opts = []
        if settings.SOSSE_PROXY:
            opts.append('--proxy-server=%s' % settings.SOSSE_PROXY.rstrip('/'))
        opts.append('--user-agent=%s' % settings.SOSSE_USER_AGENT)
        opts.append('--start-maximized')
        opts.append('--start-fullscreen')
        return opts

    @classmethod
    def _get_driver(cls, options):
        return webdriver.Chrome(options=options)

    @classmethod
    def _driver_get(cls, url):
        if cls.driver.execute_script('return window.location.href === %s' % json.dumps(url)):
            return
        dl_dir_files = cls.page_change_wait_setup()
        cls.driver.get(url)
        cls.page_change_wait(dl_dir_files)

    @classmethod
    def _get_download_file(cls):
        d = os.listdir(cls._get_download_dir())
        d = [x for x in d if not x.startswith('.')]
        if len(d) == 0:
            return None
        return os.path.join(cls._get_download_dir(), d[0])

    @classmethod
    def _get_download_dir(cls):
        return settings.SOSSE_TMP_DL_DIR + '/chromium/' + str(cls._worker_no)


class FirefoxBrowser(SeleniumBrowser):
    DRIVER_CLASS = webdriver.Firefox
    name = 'firefox'

    @classmethod
    def _get_options_obj(cls):
        options = FirefoxOptions()
        options.set_preference('browser.download.dir', settings.SOSSE_TMP_DL_DIR + '/firefox/' + str(cls._worker_no))
        options.set_preference('browser.download.folderList', 2)
        options.set_preference('browser.download.useDownloadDir', True)
        options.set_preference('browser.download.viewableInternally.enabledTypes', '')
        options.set_preference('browser.helperApps.alwaysAsk.force', False)
        options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/pdf;text/plain;application/text;text/xml;application/xml;application/octet-stream')
        options.set_preference('general.useragent.override', settings.SOSSE_USER_AGENT)

        # Ensure more secure cookie defaults, and be cosistent with Chromium's behavior
        # See https://hacks.mozilla.org/2020/08/changes-to-samesite-cookie-behavior/
        options.set_preference('network.cookie.sameSite.laxByDefault', True)
        options.set_preference('network.cookie.sameSite.noneRequiresSecure', True)

        if settings.SOSSE_PROXY:
            url = urlparse(settings.SOSSE_PROXY)
            url, port = url.netloc.rsplit(':', 1)
            port = int(port)
            options.set_preference('network.proxy.type', 1)
            options.set_preference('network.proxy.http', url)
            options.set_preference('network.proxy.http_port', port)
            options.set_preference('network.proxy.ssl', url)
            options.set_preference('network.proxy.ssl_port', port)
        return options

    @classmethod
    def _get_options(cls):
        return []

    @classmethod
    def _get_driver(cls, options):
        log_file = '/var/log/sosse/geckodriver-%i.log' % cls._worker_no

        selenium_ver = tuple(map(int, selenium.__version__.split('.')))
        if selenium_ver < (4, 9, 0):
            service = {'service_log_path': log_file}
        else:
            service = {
                'service': FirefoxService(log_output=log_file)
            }
        return webdriver.Firefox(options=options, **service)

    @classmethod
    def _driver_get(cls, url):
        if cls.driver.execute_script('return window.location.href === %s' % json.dumps(url)):
            return
        dl_dir_files = cls.page_change_wait_setup()
        # Work-around to https://github.com/SeleniumHQ/selenium/issues/4769
        # When a download starts, the regular cls.driver.get call is stuck
        cls.driver.execute_script('''
            window.location.assign(%s);
        ''' % json.dumps(url))

        if url == 'about:blank':
            raise Exception('navigating to about:blank')

        cls.page_change_wait(dl_dir_files)

    @classmethod
    def _destroy(cls):
        # Kill firefox, otherwise it can get stuck on a confirmation dialog
        # (ie, when a download is still running)
        gecko_pid = cls._driver.service.process.pid
        p = psutil.Process(gecko_pid)
        p.children()[0].kill()
        super()._destroy()

    @classmethod
    def _get_download_dir(cls):
        return settings.SOSSE_TMP_DL_DIR + '/firefox/' + str(cls._worker_no)

    @classmethod
    def _get_download_file(cls):
        for f in os.listdir(cls._get_download_dir()):
            if f.endswith('.part'):
                break
        else:
            d = os.listdir(cls._get_download_dir())
            if len(d) == 0:
                return None
            return os.path.join(cls._get_download_dir(), d[0])
        return os.path.join(cls._get_download_dir(), f)
