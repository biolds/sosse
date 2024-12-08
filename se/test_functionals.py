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

from functools import partialmethod
from hashlib import md5
from unittest import mock

from django.conf import settings
from django.test import TransactionTestCase, override_settings

from .document import Document
from .browser import ChromiumBrowser, FirefoxBrowser, RequestBrowser, SkipIndexing
from .html_asset import HTMLAsset
from .models import AuthField, Cookie, CrawlPolicy, DomainSetting, Link
from .test_mock import CleanTest, FirefoxTest


TEST_SERVER_DOMAIN = '127.0.0.1:8000'
TEST_SERVER_URL = 'http://%s/' % TEST_SERVER_DOMAIN
TEST_SERVER_USER = 'admin'
TEST_SERVER_PASS = 'admin'


class BaseFunctionalTest:
    @classmethod
    def tearDownClass(cls):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()

    def _crawl(self):
        while Document.crawl(0):
            pass


class FunctionalTest(BaseFunctionalTest):
    def test_10_simple(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=False)

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
        self.assertFalse(doc.hidden)
        self.assertFalse(doc.robotstxt_rejected)
        self.assertIsNone(doc.redirect_url)
        self.assertFalse(doc.too_many_redirects)
        self.assertEqual(doc.screenshot_count, 0)
        self.assertIsNotNone(doc.crawl_first)
        self.assertEqual(doc.crawl_first, doc.crawl_last)
        self.assertIsNone(doc.crawl_next)
        self.assertIsNone(doc.crawl_dt)
        self.assertEqual(doc.crawl_recurse, 0)
        self.assertEqual(doc.error, '')
        self.assertEqual(doc.error_hash, '')
        self.assertIsNone(doc.worker_no)
        self.assertFalse(doc.has_html_snapshot)
        self.assertFalse(doc.has_thumbnail)
        self.assertEqual(len(Document._meta.get_fields()), 33)

        self.assertEqual(Cookie.objects.count(), 0)
        self.assertEqual(Link.objects.count(), 0)

    def _reset_user_agent(self):
        from se import models
        models.UA_STR = None
        self.BROWSER_CLASS.destroy()

    def test_20_user_agent(self):
        self._reset_user_agent()
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'user-agent')
        self._check_key_val(b'user-agent', b'"%s"' %
                            settings.SOSSE_USER_AGENT.encode('utf-8'), page.content)

    @override_settings(SOSSE_USER_AGENT='')
    @override_settings(SOSSE_FAKE_USER_AGENT_BROWSER=['chrome'])
    @override_settings(SOSSE_FAKE_USER_AGENT_OS=['windows'])
    @override_settings(SOSSE_FAKE_USER_AGENT_PLATFORM=['pc'])
    def test_21_fake_ua_chrome(self):
        self._reset_user_agent()
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'user-agent')
        self.assertRegex(page.content, b"Mozilla.*Windows.*Chrome")

    # @override_settings(SOSSE_USER_AGENT='')
    # @override_settings(SOSSE_FAKE_USER_AGENT_BROWSER=['firefox'])
    # @override_settings(SOSSE_FAKE_USER_AGENT_OS=['linux'])
    # @override_settings(SOSSE_FAKE_USER_AGENT_PLATFORM=['pc'])
    # def test_22_fake_ua_firefox(self):
    #     self._reset_user_agent()
    #     page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'user-agent')
    #     self.assertRegex(page.content, b"Mozilla.*Linux.*Firefox")

    @override_settings(SOSSE_USER_AGENT='')
    @override_settings(SOSSE_FAKE_USER_AGENT_BROWSER=['safari'])
    def test_23_fake_ua_safari(self):
        self._reset_user_agent()
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'user-agent')
        self.assertRegex(page.content, b"Mozilla.*Safari")

    def test_30_gzip(self):
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'gzip')
        self._check_key_val(b'deflated', b'true', page.content)

    def test_40_deflate(self):
        page = self.BROWSER_CLASS.get(TEST_SERVER_URL + 'deflate')
        self._check_key_val(b'deflated', b'true', page.content)

    def test_50_cookies(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   mimetype_regex='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   take_screenshots=False)
        Document.queue(TEST_SERVER_URL +
                       'cookies/set?test_key=test_value', None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 2)
        self.assertEqual(Cookie.objects.count(), 1)
        cookie = Cookie.objects.first()
        self.assertEqual(cookie.name, 'test_key')
        self.assertEqual(cookie.value, 'test_value')
        self.assertEqual(cookie.domain, '127.0.0.1')
        self.assertEqual(cookie.domain_cc, None)
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
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=False)
        policy = CrawlPolicy.objects.create(url_regex='^%s.*' % TEST_SERVER_URL,
                                            recursion=CrawlPolicy.CRAWL_NEVER,
                                            recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                            default_browse_mode=self.BROWSE_MODE,
                                            snapshot_html=False,
                                            take_screenshots=False,
                                            thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                            auth_login_url_re='%sadmin/login/.*' % TEST_SERVER_URL,
                                            auth_form_selector='#login-form')
        AuthField.objects.create(
            key='username', value=TEST_SERVER_USER, crawl_policy=policy)
        AuthField.objects.create(
            key='password', value=TEST_SERVER_PASS, crawl_policy=policy)

        Document.queue(TEST_SERVER_URL + 'admin/', None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL + 'admin/')
        self.assertEqual(doc.normalized_url, '127.0.0.1:8000 admin')
        self.assertEqual(doc.title, 'Site administration | Django site admin')
        self.assertEqual(doc.normalized_title,
                         'Site administration | Django site admin')
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
        self.assertEqual(doc.screenshot_count, 0)
        self.assertIsNotNone(doc.crawl_first)
        self.assertEqual(doc.crawl_first, doc.crawl_last)
        self.assertIsNone(doc.crawl_next)
        self.assertIsNone(doc.crawl_dt)
        self.assertEqual(doc.crawl_recurse, 0)
        self.assertEqual(doc.error, '')
        self.assertEqual(doc.error_hash, '')
        self.assertIsNone(doc.worker_no)
        self.assertFalse(doc.has_html_snapshot)
        self.assertFalse(doc.has_thumbnail)
        self.assertEqual(len(Document._meta.get_fields()), 33)

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
        FILE_SIZE = settings.SOSSE_MAX_FILE_SIZE * 1024
        page = self.BROWSER_CLASS.get(
            TEST_SERVER_URL + 'download/?filesize=%i' % FILE_SIZE)
        self.assertEqual(len(page.content), FILE_SIZE)

        with self.assertRaises(SkipIndexing):
            self.BROWSER_CLASS.get(
                TEST_SERVER_URL + 'download/?filesize=%i' % (FILE_SIZE + 1))

    def test_100_remove_nav_no(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=True,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS,
                                   remove_nav_elements=CrawlPolicy.REMOVE_NAV_NO,
                                   screenshot_format=Document.SCREENSHOT_PNG)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/nav_elements.html', None, None)

        html_open = mock.mock_open()
        browser_open = mock.mock_open()
        with mock.patch('se.html_cache.open', html_open), \
                mock.patch('se.browser.open', browser_open):
            self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.get().content, 'nav')
        if self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS:
            self.assertEqual(Document.objects.get().screenshot_count, 2)

        self.assertEqual(len(html_open.mock_calls), 4)
        self.assertIn(b'</nav>', html_open.mock_calls[2].args[0])

    def test_110_remove_nav_from_index(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS,
                                   snapshot_html=True,
                                   remove_nav_elements=CrawlPolicy.REMOVE_NAV_FROM_INDEX,
                                   screenshot_format=Document.SCREENSHOT_PNG)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/nav_elements.html', None, None)

        html_open = mock.mock_open()
        with mock.patch('se.html_cache.open', html_open):
            self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.get().content, '')
        if self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS:
            self.assertEqual(Document.objects.get().screenshot_count, 2)

        self.assertEqual(len(html_open.mock_calls), 4)
        self.assertIn(b'</nav>', html_open.mock_calls[2].args[0])

    def test_120_remove_nav_from_screenshot(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=True,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS,
                                   remove_nav_elements=CrawlPolicy.REMOVE_NAV_FROM_SCREENSHOT,
                                   screenshot_format=Document.SCREENSHOT_PNG)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/nav_elements.html', None, None)

        html_open = mock.mock_open()
        with mock.patch('se.html_cache.open', html_open):
            self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.get().content, '')
        if self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS:
            self.assertEqual(Document.objects.get().screenshot_count, 1)

        self.assertEqual(len(html_open.mock_calls), 4)
        self.assertIn(b'</nav>', html_open.mock_calls[2].args[0])

    def test_130_remove_nav_from_all(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=True,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS,
                                   remove_nav_elements=CrawlPolicy.REMOVE_NAV_FROM_ALL,
                                   screenshot_format=Document.SCREENSHOT_PNG)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/nav_elements.html', None, None)

        html_open = mock.mock_open()
        with mock.patch('se.html_cache.open', html_open):
            self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.get().content, '')
        if self.BROWSE_MODE != DomainSetting.BROWSE_REQUESTS:
            self.assertEqual(Document.objects.get().screenshot_count, 1)

        self.assertEqual(len(html_open.mock_calls), 4)
        self.assertNotIn(b'</nav>', html_open.mock_calls[2].args[0])

    BIN_FILES = (
        ('test.pdf', 'application/pdf', '6756a021648506e4f25696e226be863c'),
        ('test.zip', 'application/zip', 'f2d04a4dfe9671f6a83d06fa6e2910e0'),
        ('test.wav', 'audio/x-wav', '842484461172b87fa2a02e541b279a68'),
        ('test.png', 'image/png', '71a50dbba44c78128b221b7df7bb51f1'),
        ('test.jpg', 'image/jpeg', 'fdfac8a675b1a869c0e35bea25612806'),
        ('test.mp4', 'video/mp4', 'b7507d23d616df2640065edb8b9e2504'),
    )

    def _test_bin_file_download(self, filename, mimetype, checksum):
        bin_url = TEST_SERVER_URL + 'static/pages/' + filename
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   mimetype_regex='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=True,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=False)

        Document.queue(bin_url, None, None)

        html_open = mock.mock_open()
        with mock.patch('se.html_cache.open', html_open):
            self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.get()
        self.assertEqual(doc.content, '')
        self.assertEqual(doc.mimetype, mimetype)

        self.assertEqual(HTMLAsset.objects.count(), 1)
        asset = HTMLAsset.objects.get()
        self.assertEqual(asset.url, bin_url)
        self.assertEqual(asset.ref_count, 1)

        self.assertEqual(len(html_open.mock_calls), 4)
        content_hash = md5(html_open.mock_calls[2].args[0]).hexdigest()
        self.assertEqual(content_hash, checksum)


for filename, mimetype, checksum in FunctionalTest.BIN_FILES:
    setattr(FunctionalTest,
            'test_140_file_download_%s' % mimetype.replace('/', '_').replace('-', '_'),
            partialmethod(FunctionalTest._test_bin_file_download, filename, mimetype, checksum))


class BrowserBasedFunctionalTest:
    @mock.patch('os.makedirs')
    def test_90_css_in_js(self, makedirs):
        if self.BROWSE_MODE == DomainSetting.BROWSE_REQUESTS:
            return

        makedirs.side_effect = None

        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=True,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=False)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/css_in_js.html', None, None)

        mock_open = mock.mock_open()
        with mock.patch('se.html_cache.open', mock_open):
            self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        self.assertIn(
            b'<style>body { background-color: black; }\n</style>\n  <style>body { color: white; }\n</style>', mock_open.mock_calls[2].args[0])
        self.assertNotIn(b'style id="test"', mock_open.mock_calls[2].args[0])
        self.assertEqual(mock_open.mock_calls[0].args[0], settings.SOSSE_HTML_SNAPSHOT_DIR +
                         'http,3A/127.0.0.1,3A8000/static/pages/css_in_js.html_405fd23df0.html')

    def test_140_file_download_from_blank(self):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()

        Cookie.objects.create(domain='127.0.0.1',
                              name='test',
                              value='test',
                              inc_subdomain=False,
                              secure=False)
        FILE_SIZE = 1024
        page = self.BROWSER_CLASS.get(
            TEST_SERVER_URL + 'download/?filesize=%i' % FILE_SIZE)
        self.assertEqual(len(page.content), FILE_SIZE, page.content)


class RequestsFunctionalTest(FunctionalTest, CleanTest, TransactionTestCase):
    BROWSE_MODE = DomainSetting.BROWSE_REQUESTS
    BROWSER_CLASS = RequestBrowser


class ChromiumFunctionalTest(FunctionalTest, CleanTest, BrowserBasedFunctionalTest, TransactionTestCase):
    BROWSE_MODE = DomainSetting.BROWSE_CHROMIUM
    BROWSER_CLASS = ChromiumBrowser


class FirefoxFunctionalTest(FunctionalTest, FirefoxTest, BrowserBasedFunctionalTest, TransactionTestCase):
    BROWSE_MODE = DomainSetting.BROWSE_FIREFOX
    BROWSER_CLASS = FirefoxBrowser


class BrowserDetectFunctionalTest(BaseFunctionalTest, TransactionTestCase):
    def test_10_detect_browser(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=DomainSetting.BROWSE_DETECT,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=False)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/browser_detect_js.html', None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL +
                         'static/pages/browser_detect_js.html')
        self.assertIn('has JS', doc.content)

        self.assertEqual(DomainSetting.objects.count(), 1)
        domain = DomainSetting.objects.first()
        self.assertEqual(domain.domain, TEST_SERVER_DOMAIN)
        self.assertEqual(domain.browse_mode, DomainSetting.BROWSE_CHROMIUM)

    def test_20_detect_browser(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=DomainSetting.BROWSE_DETECT,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
                                   take_screenshots=False)

        Document.queue(TEST_SERVER_URL +
                       'static/pages/browser_detect_no_js.html', None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL +
                         'static/pages/browser_detect_no_js.html')
        self.assertIn('has no JS', doc.content)

        self.assertEqual(DomainSetting.objects.count(), 1)
        domain = DomainSetting.objects.first()
        self.assertEqual(domain.domain, TEST_SERVER_DOMAIN)
        self.assertEqual(domain.browse_mode, DomainSetting.BROWSE_REQUESTS)
