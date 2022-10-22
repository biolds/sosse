import json
import logging
import os
import pytz
import traceback
from datetime import datetime
from hashlib import md5
from time import sleep
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from django.conf import settings
import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


crawl_logger = logging.getLogger('crawler')


class Page:
    def __init__(self, url, content, browser):
        self.url = url
        self.content = content
        self.got_redirect = False
        self.title = None
        self.soup = None
        self.browser = browser

    def get_soup(self):
        if self.soup:
            return self.soup
        self.soup = BeautifulSoup(self.content, 'html5lib')

        # Remove <template> tags as BS extract its text
        for elem in self.soup.find_all('template'):
            elem.extract()
        return self.soup

    def get_links(self, keep_params):
        from .models import absolutize_url

        for a in self.get_soup().find_all('a'):
            if a.get('href'):
                u = absolutize_url(self.url, a.get('href').strip(), keep_params, False)
                if '#' in u:
                    raise Exception('aaa %s %s %s' % (u, self.url, a.get('href')))
                yield u


class Browser:
    @classmethod
    def init(cls):
        RequestBrowser.init()
        SeleniumBrowser.init()

    @classmethod
    def destroy(cls):
        RequestBrowser.destroy()
        SeleniumBrowser.destroy()


class RequestBrowser(Browser):
    @classmethod
    def init(cls):
        pass

    @classmethod
    def destroy(cls):
        pass

    @classmethod
    def _page_from_request(cls, r, raw=False):
        content = r.content
        if not raw:
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                # Binary file
                pass

        url = unquote(r.url)
        page = Page(url,
                    content,
                    cls)
        parsed = page.get_soup()
        page.title = parsed.title and parsed.title.string
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

        if _cookies:
            Cookie.set(url, _cookies)

    @classmethod
    def _get_cookies(cls, url):
        from .models import Cookie
        jar = requests.cookies.RequestsCookieJar()

        for c in Cookie.get_from_url(url):
            jar.set(c.name, c.value, domain=c.domain)
        return jar

    @classmethod
    def _get_headers(cls):
        return {
            'User-Agent': settings.SOSSE_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }

    @classmethod
    def get(cls, url, raw=False, check_status=False):
        from .models import absolutize_url, CrawlPolicy
        got_redirect = False
        page = None
        did_redirect = False
        redirects = 256
        while redirects > 0:
            redirects -= 1

            cookies = cls._get_cookies(url)
            r = requests.get(url, cookies=cookies, headers=cls._get_headers())
            cls._set_cookies(url, r.cookies)

            if check_status:
                r.raise_for_status()

            if len(r.history):
                did_redirect = True

            page = cls._page_from_request(r, raw)
            for meta in page.get_soup().find_all('meta'):
                if meta.get('http-equiv', '').lower() == 'refresh' and meta.get('content', ''):
                    # handle redirect
                    dest = meta.get('content')

                    if ';' in dest:
                        dest = dest.split(';', 1)[1]

                    if dest.startswith('url='):
                        dest = dest[4:]

                    url = absolutize_url(url, dest)
                    did_redirect = True
                    break
            else:
                break

        page.got_redirect = did_redirect
        return page

    @classmethod
    def try_auth(cls, page, url, crawl_policy):
        from .models import absolutize_url

        parsed = page.get_soup()
        form = parsed.select(crawl_policy.auth_form_selector)

        if len(form) == 0:
            raise Exception('Could not find element with CSS selector: %s' % crawl_policy.auth_form_selector)

        if len(form) > 1:
            raise Exception('Found multiple element with CSS selector: %s' % crawl_policy.auth_form_selector)

        form = form[0]
        payload = {}
        for elem in form.find_all('input'):
            if elem.get('name'):
                payload[elem.get('name')] = elem.get('value')

        for f in crawl_policy.authfield_set.values('key', 'value'):
            payload[f['key']] = f['value']

        post_url = form.get('action')
        post_url = absolutize_url(page.url, post_url, True, False)
        cookies = cls._get_cookies(post_url)
        crawl_logger.debug('authenticating to %s with %s (cookie: %s)' % (post_url, payload, cookies))
        r = requests.post(post_url,
                          data=payload,
                          cookies=cookies,
                          allow_redirects=False,
                          headers=cls._get_headers())
        cls._set_cookies(post_url, r.cookies)

        crawl_logger.debug('auth returned cookie: %s' % r.cookies)
        crawl_policy.save()

        if r.status_code != 302:
            crawl_logger.debug('no redirect after auth')
            return cls._page_from_request(r)

        location = r.headers.get('location')
        if not location:
            raise Exception('No location in the redirection')

        location = absolutize_url(r.url, location, True, False)
        crawl_logger.debug('got redirected to %s after authentication' % location)
        cookies = cls._get_cookies(location)
        r = requests.get(location, cookies=cookies, headers=cls._get_headers())
        cls._set_cookies(location, r.cookies)
        r.raise_for_status()
        crawl_logger.debug('content:\n%s' % r.content)
        crawl_logger.debug('authentication done')
        return cls._page_from_request(r)


def retry(f):
    def _retry(*args, **kwargs):
        count = 0
        while count <= settings.SOSSE_BROWSER_CRASH_RETRY:
            try:
                r = f(*args, **kwargs)
                crawl_logger.debug('%s succeeded' % f)
                return r
            except WebDriverException as e:
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
    driver = None
    cookie_loaded = []
    COOKIE_LOADED_SIZE = 1024

    @classmethod
    def init(cls):
        from .models import CrawlPolicy
        options = Options()
        options.binary_location = "/usr/bin/chromium"
        options.add_argument('--user-agent=%s' % settings.SOSSE_USER_AGENT)
        options.add_argument('--start-maximized')
        options.add_argument('--start-fullscreen')
        options.add_argument('--window-size=%s,%s' % cls.screen_size())
        options.add_argument("--enable-precise-memory-info")
        options.add_argument("--disable-default-apps")
        options.add_argument("--incognito")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")

        # Disable downloads
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.delete_all_cookies()

    @classmethod
    def destroy(cls):
        if cls.driver:
            # Ignore errors in case the browser crashed
            try:
                cls.driver.close()
            except WebDriverException:
                pass

            try:
                cls.driver.quit()
            except WebDriverException:
                pass

    @classmethod
    def _get_page(cls):
        # Wait for page being ready
        retry = settings.SOSSE_JS_STABLE_RETRY
        while retry > 0:
            retry -= 1
            if cls.driver.execute_script('return document.readyState;') == 'complete':
                break

        # Wait for page content to be stable
        retry = settings.SOSSE_JS_STABLE_RETRY
        previous_content = None
        content = None

        while retry > 0:
            retry -= 1

            content = cls.driver.page_source

            if content == previous_content:
                break
            previous_content = content
            sleep(settings.SOSSE_JS_STABLE_TIME)

        page = Page(cls.driver.current_url,
                    content,
                    cls)
        page.title = cls.driver.title
        return page

    @classmethod
    def _save_cookies(cls, url):
        from .models import Cookie
        _cookies = []
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

            _cookies.append(c)

        if _cookies:
            Cookie.set(url, _cookies)

    @classmethod
    def _load_cookies(cls, url):
        from .models import Cookie

        # Cookies can only be set to the same domain,
        # so first we navigate to the correct location
        current_url = urlparse(cls.driver.current_url)
        target_url = urlparse(url)
        if current_url.netloc != target_url.netloc:
            cls.driver.get(url)

        cls.driver.delete_all_cookies()
        for c in Cookie.get_from_url(url):
            cookie = {
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
                'path': c.path,
                'secure': c.secure,
                'httpOnly': c.http_only,
                'sameSite': c.same_site,
            }
            if c.expires:
                cookie['expiry'] = int(c.expires.strftime('%s'))

            try:
                cls.driver.add_cookie(cookie)
            except:
                raise Exception(cookie)

    @classmethod
    def _browser_get(cls, url):
        cls._load_cookies(url)
        cls.driver.get(url)
        cls._save_cookies(url)

    @classmethod
    @retry
    def get(cls, url):
        current_url = cls.driver.current_url

        # Clear the download dir
        for f in os.listdir('.'):
            if f != 'core':
                crawl_logger.warning('Deleting stale download file %s (you may fix the issue by adjusting "dl_check_*" variables in the conf)' % f)
            os.unlink(f)

        cls._browser_get(url)

        if ((current_url != url and cls.driver.current_url == current_url) or # If we got redirected to the url that was previously set in the browser
                cls.driver.current_url == 'data:,'): # The url can be "data:," during a few milliseconds when the download starts
            page = cls._handle_download(url)
            if page:
                return page

        page = cls._get_page()

        if url != page.url:
            page.got_redirect = True

        return page

    @classmethod
    def _handle_download(cls, url):
        retry = settings.SOSSE_DL_CHECK_RETRY
        while retry:
            if len(os.listdir('.')) != 0:
                break
            crawl_logger.debug('no download in progress')
            sleep(settings.SOSSE_DL_CHECK_TIME)
            retry -= 1
        else:
            if len(os.listdir('.')) == 0: # redo the check in case SOSSE_DL_CHECK_RETRY == 0
                crawl_logger.debug('no download has started')
                return

        crawl_logger.debug('Download in progress: %s' % os.listdir('.'))
        sizes = [os.stat(f).st_size for f in os.listdir('.')]
        while True:
            sleep(0.1)
            _sizes = [os.stat(f).st_size for f in os.listdir('.')]
            if sizes == _sizes:
                break
            sizes = _sizes

        crawl_logger.debug('Download done: %s' % os.listdir('.'))
        with open(os.listdir('.')[0], 'rb') as f:
            content = f.read(1024 * 1024)

        page = Page(url, content, cls)

        # Remove all files in case multiple were downloaded
        for f in os.listdir('.'):
            os.unlink(f)
        return page

    @classmethod
    def screenshot_name(cls, url):
        filename = md5(url.encode('utf-8')).hexdigest()
        base_dir = filename[:2]
        return base_dir, filename

    @classmethod
    def screen_size(cls):
        w, h = settings.SOSSE_SCREENSHOTS_SIZE.split('x')
        return int(w), int(h)

    @classmethod
    @retry
    def take_screenshots(cls, url):
        base_dir, filename = cls.screenshot_name(url)
        d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, base_dir)
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, filename)

        width, height = cls.screen_size()
        cls.driver.set_window_rect(0, 0, *cls.screen_size())
        cls.driver.execute_script('document.body.style.overflow = "hidden"');
        doc_height = cls.driver.execute_script('''
            const body = document.body;
            const html = document.documentElement;
            return height = Math.max(body.scrollHeight, body.offsetHeight,
                                   html.clientHeight, html.scrollHeight, html.offsetHeight);
        ''')

        img_no = 0
        while (img_no + 1) * height < doc_height:
            cls.scroll_to_page(img_no)
            cls.driver.get_screenshot_as_file('%s_%s.png' % (f, img_no))
            img_no += 1

        remaining = doc_height - (img_no * height)
        if remaining > 0:
            cls.driver.set_window_rect(0, 0, width, remaining)
            cls.scroll_to_page(img_no)
            cls.driver.get_screenshot_as_file('%s_%s.png' % (f, img_no))
            img_no += 1

        return os.path.join(base_dir, filename), img_no

    @classmethod
    def scroll_to_page(cls, page_no):
        _, height = cls.screen_size()
        cls.driver.execute_script('window.scroll(0, %s)' % (page_no * height))

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
            raise Exception('Could not find auth element with CSS selector: %s' % crawl_policy.auth_form_selector)

        if len(form) > 1:
            raise Exception('Found multiple auth element with CSS selector: %s' % crawl_policy.auth_form_selector)

        crawl_logger.debug('form found')
        form = form[0]
        for f in crawl_policy.authfield_set.values('key', 'value'):
            elem = cls._find_elements_by_selector(form, 'input[name="%s"]' % f['key'])
            if len(elem) != 1:
                raise Exception('Found %s multiple input element when trying to set auth field %s' % (len(elem), f['key']))
            elem[0].send_keys(f['value'])
            crawl_logger.debug('settings %s = %s on %s' % (f['key'], f['value'], elem[0]))

        form.submit()
        crawl_logger.debug('submitting')
        cls._save_cookies(cls.driver.current_url)
        crawl_logger.debug('got cookie %s' % crawl_policy.auth_cookies)

        if cls.driver.current_url != url:
            return cls.get(url)

        return cls._get_page()
