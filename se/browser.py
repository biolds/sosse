import json
import logging
import os
from hashlib import md5
from time import sleep

from bs4 import BeautifulSoup
from django.conf import settings
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from urllib.parse import unquote


crawl_logger = logging.getLogger('crawler')


class Page:
    def __init__(self, url, content, cookies, browser):
        self.url = url
        self.content = content
        self.cookies = cookies
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
                    dict(r.cookies),
                    cls)
        parsed = page.get_soup()
        page.title = parsed.title and parsed.title.string
        return page

    @classmethod
    def get(cls, url, raw=False, check_status=False):
        from .models import absolutize_url, CrawlPolicy
        got_redirect = False
        page = None
        did_redirect = False
        redirects = 256
        while redirects > 0:
            redirects -= 1

            cookies = CrawlPolicy.get_cookies(url)
            r = requests.get(url, cookies=cookies, headers={'User-Agent': settings.SOSSE_USER_AGENT})
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
        crawl_logger.debug('authenticating to %s with %s (cookie: %s)' % (post_url, payload, page.cookies))
        r = requests.post(post_url,
                          data=payload,
                          cookies=page.cookies,
                          allow_redirects=False,
                          headers={'User-Agent': settings.SOSSE_USER_AGENT})

        crawl_policy.auth_cookies = json.dumps(dict(r.cookies))
        crawl_logger.debug('auth returned cookie: %s' % crawl_policy.auth_cookies)
        crawl_policy.save()

        if r.status_code != 302:
            crawl_logger.debug('no redirect after auth')
            return cls._page_from_request(r)

        location = r.headers.get('location')
        if not location:
            raise Exception('No location in the redirection')

        location = absolutize_url(r.url, location, True, False)
        crawl_logger.debug('got redirected to %s after authentication' % location)
        r = requests.get(location, cookies=r.cookies, headers={'User-Agent': settings.SOSSE_USER_AGENT})
        r.raise_for_status()
        crawl_logger.debug('content:\n%s' % r.content)
        crawl_logger.debug('authentication done')
        return cls._page_from_request(r)


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
        options.add_argument("--disable-popup-blocking")
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
            cls.driver.close()
            cls.driver.quit()

    @classmethod
    def _get_page(cls):
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
                    None,
                    cls)
        page.title = cls.driver.title
        return page

    @classmethod
    def _cache_cookie(cls, crawl_policy):
        cls.cookie_loaded.append(crawl_policy.id)

        if len(cls.cookie_loaded) > cls.COOKIE_LOADED_SIZE:
            cls.cookie_loaded = cls.cookie_loaded[1:]

    @classmethod
    def _load_cookie(cls, url):
        from .models import CrawlPolicy
        crawl_policy = CrawlPolicy.get_from_url(url)
        if crawl_policy is None:
            return

        if crawl_policy.id in cls.cookie_loaded:
            return False

        cls._cache_cookie(crawl_policy)

        if crawl_policy.auth_cookies:
            cookies = json.loads(crawl_policy.auth_cookies)
            for name, value in cookies.items():
                cls.driver.add_cookie({'name': name, 'value': value})
        return True

    @classmethod
    def get(cls, url):
        current_url = cls.driver.current_url

        # Clear the download dir
        for f in os.listdir('.'):
            crawl_logger.warning('Deleting stale download file %s (you may fix the issue by adjusting "dl_check_*" variables in the conf)' % f)
            os.unlink(f)

        cls.driver.get(url)
        if cls._load_cookie(url):
            current_url = cls.driver.current_url
            cls.driver.get(url)

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

        page = Page(url, content, None, cls)

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
        cookies = dict([(cookie['name'], cookie['value']) for cookie in cls.driver.get_cookies()])
        crawl_policy.auth_cookies = json.dumps(cookies)
        crawl_policy.save()
        cls._cache_cookie(crawl_policy)
        crawl_logger.debug('got cookie %s' % crawl_policy.auth_cookies)

        if cls.driver.current_url != url:
            return cls.get(url)

        return cls._get_page()
