import json
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
            content = content.decode('utf-8')
        page = Page(r.url,
                    content,
                    dict(r.cookies),
                    cls)
        parsed = page.get_soup()
        page.title = parsed.title and parsed.title.string
        return page

    @classmethod
    def get(cls, url, raw=False, check_status=False):
        from .models import absolutize_url, UrlPolicy
        got_redirect = False
        page = None
        did_redirect = False
        redirects = 256
        while redirects > 0:
            redirects -= 1

            cookies = UrlPolicy.get_cookies(url)
            r = requests.get(url, cookies=cookies)
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
    def try_auth(cls, page, url, url_policy):
        from .models import absolutize_url

        parsed = page.get_soup()
        form = parsed.select(url_policy.auth_form_selector)

        if len(form) == 0:
            raise Exception('Could not find element with CSS selector: %s' % url_policy.auth_form_selector)

        if len(form) > 1:
            raise Exception('Found multiple element with CSS selector: %s' % url_policy.auth_form_selector)

        form = form[0]
        payload = {}
        for elem in form.find_all('input'):
            if elem.get('name'):
                payload[elem.get('name')] = elem.get('value')

        for f in url_policy.authfield_set.values('key', 'value'):
            payload[f['key']] = f['value']

        post_url = form.get('action')
        post_url = absolutize_url(page.url, post_url)
        r = requests.post(post_url, data=payload, cookies=page.cookies, allow_redirects=False)

        url_policy.auth_cookies = json.dumps(dict(r.cookies))
        url_policy.save()

        if r.status_code != 302:
            return cls._page_from_request(r)

        location = r.headers.get('location')
        if not location:
            raise Exception('No location in the redirection')

        location = absolutize_url(r.url, location)
        r = requests.get(location, cookies=r.cookies)
        r.raise_for_status()
        return cls._page_from_request(r)


class SeleniumBrowser(Browser):   
    driver = None
    cookie_loaded = []
    COOKIE_LOADED_SIZE = 1024

    @classmethod
    def init(cls):
        from .models import UrlPolicy
        options = Options()
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("start-maximized")
        options.add_argument('--start-fullscreen')
        options.add_argument('--window-size=%s,%s' % cls.screen_size())
        options.add_argument("--enable-precise-memory-info")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-default-apps")
        options.add_argument("--incognito")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.delete_all_cookies()

    @classmethod
    def destroy(cls):
        if cls.driver:
            cls.driver.close()
            cls.driver.quit()

    @classmethod
    def _get_page(cls):
        retry = 100
        previous_content = None
        content = None

        while retry > 0:
            retry -= 1

            content = cls.driver.page_source

            if content == previous_content:
                break
            previous_content = content
            sleep(0.1)

        page = Page(unquote(cls.driver.current_url),
                    content,
                    None,
                    cls)
        page.title = cls.driver.title
        return page

    @classmethod
    def _cache_cookie(cls, url_policy):
        cls.cookie_loaded.append(url_policy.id)

        if len(cls.cookie_loaded) > cls.COOKIE_LOADED_SIZE:
            cls.cookie_loaded = cls.cookie_loaded[1:]

    @classmethod
    def _load_cookie(cls, url):
        from .models import UrlPolicy
        url_policy = UrlPolicy.get_from_url(url)
        if url_policy is None:
            return

        if url_policy.id in cls.cookie_loaded:
            return False

        cls._cache_cookie(url_policy)

        if url_policy.auth_cookies:
            cookies = json.loads(url_policy.auth_cookies)
            for name, value in cookies.items():
                cls.driver.add_cookie({'name': name, 'value': value})
        return True

    @classmethod
    def get(cls, url):
        cls.driver.get(url)
        if cls._load_cookie(url):
            cls.driver.get(url)

        page = cls._get_page()

        if url != cls.driver.current_url:
            page.got_redirect = True

        return page

    @classmethod
    def screenshot_name(cls, url):
        filename = md5(url.encode('utf-8')).hexdigest()
        base_dir = filename[:2]
        return base_dir, filename

    @classmethod
    def screen_size(cls):
        w, h = settings.OSSE_SCREENSHOTS_SIZE.split('x')
        return int(w), int(h)

    @classmethod
    def take_screenshots(cls, url):
        base_dir, filename = cls.screenshot_name(url)
        d = os.path.join(settings.OSSE_SCREENSHOTS_DIR, base_dir)
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
    def try_auth(cls, page, url, url_policy):
        form = cls.driver.find_elements_by_css_selector(url_policy.auth_form_selector)

        if len(form) == 0:
            raise Exception('Could not find element with CSS selector: %s' % url_policy.auth_form_selector)

        if len(form) > 1:
            raise Exception('Found multiple element with CSS selector: %s' % url_policy.auth_form_selector)

        form = form[0]
        for f in url_policy.authfield_set.values('key', 'value'):
            elem = form.find_element_by_css_selector('input[name="%s"]' % f['key'])
            elem.send_keys(f['value'])

        form.submit()
        cookies = dict([(cookie['name'], cookie['value']) for cookie in cls.driver.get_cookies()])
        url_policy.auth_cookies = json.dumps(cookies)
        url_policy.save()
        cls._cache_cookie(url_policy)

        if cls.driver.current_url != url:
            return cls.get(url)

        return cls._get_page()
