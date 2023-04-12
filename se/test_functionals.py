# Copyright 2022-2023 Laurent Defert
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

from django.test import TestCase

from .browser import Browser, RequestBrowser, SeleniumBrowser, SkipIndexing
from .models import AuthField, Cookie, CrawlPolicy, Document, DomainSetting, Link


TEST_SERVER_URL = 'http://127.0.0.1:8000/'
TEST_SERVER_USER = 'admin'
TEST_SERVER_PASS = 'admin'


class FunctionalTest:
    @classmethod
    def setUpClass(cls):
        Browser.init()

    @classmethod
    def tearDownClass(cls):
        Browser.destroy()

    def _crawl(self):
        while Document.crawl(0):
            pass

    def test_10_simple(self):
        CrawlPolicy.objects.create(url_regex='.*',
                                   condition=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE)

        Document.queue(TEST_SERVER_URL, None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL)
        self.assertEqual(doc.normalized_url, '127.0.0.1:8000')
        self.assertEqual(doc.title, TEST_SERVER_URL)
        self.assertEqual(doc.normalized_title, 'http://127.0.0.1:8000/')
        self.assertIn('This page.', doc.content)
        self.assertIn('This page.', doc.normalized_content)
        self.assertIsNotNone(doc.content_hash)
        self.assertEqual(doc.lang_iso_639_1, 'en')
        self.assertEqual(doc.mimetype, 'text/html')
        self.assertIsNotNone(doc.favicon)
        self.assertEqual(doc.favicon.url, TEST_SERVER_URL + 'favicon.ico')
        self.assertIsNone(doc.favicon.content)
        self.assertIsNone(doc.favicon.mimetype)
        self.assertTrue(doc.favicon.missing)
        self.assertFalse(doc.robotstxt_rejected)
        self.assertIsNone(doc.redirect_url)
        self.assertFalse(doc.too_many_redirects)
        self.assertIsNone(doc.screenshot_file)
        self.assertIsNone(doc.screenshot_count)
        self.assertIsNotNone(doc.crawl_first)
        self.assertEqual(doc.crawl_first, doc.crawl_last)
        self.assertIsNone(doc.crawl_next)
        self.assertIsNone(doc.crawl_dt)
        self.assertEqual(doc.crawl_recurse, 0)
        self.assertEqual(doc.error, '')
        self.assertEqual(doc.error_hash, '')
        self.assertIsNone(doc.worker_no)

        self.assertEqual(Cookie.objects.count(), 0)
        self.assertEqual(Link.objects.count(), 0)

    def test_20_user_agent(self):
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'user-agent')
        self.assertIn('"user-agent": "SOSSE"', page.content)

    def test_30_gzip(self):
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'gzip')
        self.assertIn('"deflated": true', page.content)

    def test_40_deflate(self):
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'deflate')
        self.assertIn('"deflated": true', page.content)

    def test_50_cookies(self):
        CrawlPolicy.objects.create(url_regex='.*',
                                   mimetype_regex='.*',
                                   condition=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE)
        Document.queue(TEST_SERVER_URL + 'cookies/set?test_key=test_value', None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 2)
        self.assertEqual(Cookie.objects.count(), 1)
        cookie = Cookie.objects.first()
        self.assertEqual(cookie.name, 'test_key')
        self.assertEqual(cookie.value, 'test_value')
        self.assertEqual(cookie.domain, '127.0.0.1')
        self.assertIsNone(cookie.domain_cc)
        self.assertIsNone(cookie.expires)
        self.assertFalse(cookie.http_only)
        self.assertFalse(cookie.inc_subdomain)
        self.assertEqual(cookie.path, '/')
        self.assertEqual(cookie.same_site, 'Lax')
        self.assertFalse(cookie.secure)

    def test_60_cookie_delete(self):
        self.test_50_cookies()

        Document.queue(TEST_SERVER_URL + 'cookies/delete?test_key', None, None)
        self._crawl()

        # Clear the expired cookie
        Cookie.get_from_url(TEST_SERVER_URL)

        self.assertEqual(Document.objects.count(), 3)
        self.assertEqual(Cookie.objects.count(), 0)

    def test_70_authentication(self):
        CrawlPolicy.objects.create(url_regex='.*',
                                   condition=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE)
        policy = CrawlPolicy.objects.create(url_regex='^%s.*' % TEST_SERVER_URL,
                                            condition=CrawlPolicy.CRAWL_NEVER,
                                            recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                            default_browse_mode=self.BROWSE_MODE,
                                            auth_login_url_re='%sadmin/login/.*' % TEST_SERVER_URL,
                                            auth_form_selector='#login-form')
        AuthField.objects.create(key='username', value=TEST_SERVER_USER, crawl_policy=policy)
        AuthField.objects.create(key='password', value=TEST_SERVER_PASS, crawl_policy=policy)

        Document.queue(TEST_SERVER_URL + 'admin/', None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL + 'admin/')
        self.assertEqual(doc.normalized_url, '127.0.0.1:8000 admin')
        self.assertEqual(doc.title, 'Site administration | Django site admin')
        self.assertEqual(doc.normalized_title, 'Site administration | Django site admin')
        self.assertIn('Welcome, admin .', doc.content)
        self.assertIn('Welcome, admin .', doc.normalized_content)
        self.assertIsNotNone(doc.content_hash)
        self.assertEqual(doc.lang_iso_639_1, 'en')
        self.assertEqual(doc.mimetype, 'text/html')
        self.assertIsNotNone(doc.favicon)
        self.assertEqual(doc.favicon.url, TEST_SERVER_URL + 'favicon.ico')
        self.assertIsNone(doc.favicon.content)
        self.assertIsNone(doc.favicon.mimetype)
        self.assertTrue(doc.favicon.missing)
        self.assertFalse(doc.robotstxt_rejected)
        self.assertIsNone(doc.redirect_url)
        self.assertFalse(doc.too_many_redirects)
        self.assertIsNone(doc.screenshot_file)
        self.assertIsNone(doc.screenshot_count)
        self.assertIsNotNone(doc.crawl_first)
        self.assertEqual(doc.crawl_first, doc.crawl_last)
        self.assertIsNone(doc.crawl_next)
        self.assertIsNone(doc.crawl_dt)
        self.assertEqual(doc.crawl_recurse, 0)
        self.assertEqual(doc.error, '')
        self.assertEqual(doc.error_hash, '')
        self.assertIsNone(doc.worker_no)

        self.assertEqual(Cookie.objects.count(), 2)
        cookies = Cookie.objects.order_by('name').values()
        self.assertEqual(cookies[0]['name'], 'csrftoken')
        self.assertEqual(cookies[0]['domain'], '127.0.0.1')
        self.assertIsNone(cookies[0]['domain_cc'])
        self.assertIsNotNone(cookies[0]['expires'])
        self.assertFalse(cookies[0]['http_only'])
        self.assertFalse(cookies[0]['inc_subdomain'])
        self.assertEqual(cookies[0]['path'], '/')
        self.assertEqual(cookies[0]['same_site'], 'Lax')
        self.assertFalse(cookies[0]['secure'])
        self.assertRegex(cookies[0]['value'], '[A-Za-z0-9]+')

        self.assertEqual(cookies[1]['name'], 'sessionid')
        self.assertEqual(cookies[1]['domain'], '127.0.0.1')
        self.assertIsNone(cookies[1]['domain_cc'])
        self.assertIsNotNone(cookies[1]['expires'])
        self.assertTrue(cookies[1]['http_only'])
        self.assertFalse(cookies[1]['inc_subdomain'])
        self.assertEqual(cookies[1]['path'], '/')
        self.assertEqual(cookies[1]['same_site'], 'Lax')
        self.assertFalse(cookies[1]['secure'])
        self.assertRegex(cookies[1]['value'], '[a-z0-9]+')

        self.assertEqual(Link.objects.count(), 0)

    def test_80_file_too_big(self):
        FILE_SIZE = 500 * 1024
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'download/?filesize=%i' % FILE_SIZE)
        self.assertEqual(len(page.content), FILE_SIZE)

        with self.assertRaises(SkipIndexing):
            self.BROWSER_CLASS.get(TEST_SERVER_URL + 'download/?filesize=%i' % (FILE_SIZE + 1))


class RequestsFunctionalTest(FunctionalTest, TestCase):
    BROWSE_MODE = DomainSetting.BROWSE_REQUESTS
    BROWSER_CLASS = RequestBrowser


class SeleniumFunctionalTest(FunctionalTest, TestCase):
    BROWSE_MODE = DomainSetting.BROWSE_SELENIUM
    BROWSER_CLASS = SeleniumBrowser
