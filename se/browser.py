import json
from time import sleep

from bs4 import BeautifulSoup
from django.conf import settings
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


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

    def get_links(self):
        from .models import absolutize_url

        for a in self.get_soup().find_all('a'):
            if a.get('href'):
                u = absolutize_url(self.url, a.get('href'))
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
    def get(cls, url, raw=False):
        from .models import absolutize_url, DomainPolicy
        got_redirect = False
        page = None
        did_redirect = False
        redirects = 256
        while redirects > 0:
            redirects -= 1

            cookies = DomainPolicy.get_cookies(url)
            r = requests.get(url, cookies=cookies)

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
    def try_auth(cls, page, url, domain_policy):
        from .models import absolutize_url

        parsed = page.get_soup()
        form = parsed.select(domain_policy.auth_form_selector)

        if len(form) == 0:
            raise Exception('Could not find element with CSS selector: %s' % domain_policy.auth_form_selector)

        if len(form) > 1:
            raise Exception('Found multiple element with CSS selector: %s' % domain_policy.auth_form_selector)

        form = form[0]
        payload = {}
        for elem in form.find_all('input'):
            if elem.get('name'):
                payload[elem.get('name')] = elem.get('value')

        for f in domain_policy.authfield_set.values('key', 'value'):
            payload[f['key']] = f['value']

        post_url = form.get('action')
        post_url = absolutize_url(page.url, post_url)
        r = requests.post(post_url, data=payload, cookies=page.cookies, allow_redirects=False)

        domain_policy.auth_cookies = json.dumps(dict(r.cookies))
        domain_policy.save()

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
        from .models import DomainPolicy
        options = Options()
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("start-maximized")
        options.add_argument("--window-size=1920,1080")
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

            #content = cls.driver.execute_script('return document.getElementsByTagName("body")[0].innerHTML')
            #content = '<html>%s</html>' % content
            content = cls.driver.page_source

            if content == previous_content:
                break
            previous_content = content
            sleep(0.1)

        page = Page(cls.driver.current_url,
                    content,
                    None,
                    cls)
        page.title = cls.driver.title
        return page

    @classmethod
    def _cache_cookie(cls, domain_policy):
        cls.cookie_loaded.append(domain_policy.id)

        if len(cls.cookie_loaded) > cls.COOKIE_LOADED_SIZE:
            cls.cookie_loaded = cls.cookie_loaded[1:]

    @classmethod
    def _load_cookie(cls, url):
        from .models import DomainPolicy
        domain_policy = DomainPolicy.get_from_url(url)
        if domain_policy is None:
            return

        if domain_policy.id in cls.cookie_loaded:
            return False

        cls._cache_cookie(domain_policy)

        if domain_policy.auth_cookies:
            cookies = json.loads(domain_policy.auth_cookies)
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

        #f = page.url.replace('/', '_')
        #cls.driver.get_screenshot_as_file('/tmp/%s.png' % f)
        return page


    @classmethod
    def try_auth(cls, page, url, domain_policy):
        form = cls.driver.find_elements_by_css_selector(domain_policy.auth_form_selector)

        if len(form) == 0:
            raise Exception('Could not find element with CSS selector: %s' % domain_policy.auth_form_selector)

        if len(form) > 1:
            raise Exception('Found multiple element with CSS selector: %s' % domain_policy.auth_form_selector)

        form = form[0]
        for f in domain_policy.authfield_set.values('key', 'value'):
            elem = form.find_element_by_css_selector('input[name="%s"]' % f['key'])
            elem.send_keys(f['value'])

        form.submit()
        cookies = dict([(cookie['name'], cookie['value']) for cookie in cls.driver.get_cookies()])
        domain_policy.auth_cookies = json.dumps(cookies)
        domain_policy.save()
        cls._cache_cookie(domain_policy)

        if cls.driver.current_url != url:
            return cls.get(url)

        return cls._get_page()
