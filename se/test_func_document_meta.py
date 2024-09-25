# Copyright 2024 Laurent Defert
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

from hashlib import md5

from django.conf import settings
from django.test import TransactionTestCase
from PIL import Image

from .document import Document
from .browser import ChromiumBrowser, FirefoxBrowser, RequestBrowser
from .models import CrawlPolicy, DomainSetting


TEST_SERVER_DOMAIN = '127.0.0.1:8000'
TEST_SERVER_URL = f'http://{TEST_SERVER_DOMAIN}/'
TEST_SERVER_URL_MD5 = md5(TEST_SERVER_URL.encode('utf-8')).hexdigest()
TEST_SERVER_THUMBNAIL_FILE = os.path.join(settings.SOSSE_THUMBNAILS_DIR,
                                          TEST_SERVER_URL_MD5[:2],
                                          TEST_SERVER_URL_MD5) + '.jpg'

TEST_SERVER_OGP_URL = f'{TEST_SERVER_URL}ogp/'
TEST_SERVER_OGP_URL_MD5 = md5(TEST_SERVER_OGP_URL.encode('utf-8')).hexdigest()
TEST_SERVER_OGP_THUMBNAIL_FILE = os.path.join(settings.SOSSE_THUMBNAILS_DIR,
                                              TEST_SERVER_OGP_URL_MD5[:2],
                                              TEST_SERVER_OGP_URL_MD5) + '.jpg'


class BaseFunctionalTest:
    @classmethod
    def tearDownClass(cls):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()

    def setUp(self):
        self.assertEqual(Document.objects.count(), 0)

    def tearDown(self):
        for f in (TEST_SERVER_THUMBNAIL_FILE, TEST_SERVER_OGP_THUMBNAIL_FILE):
            if os.path.isfile(f):
                os.unlink(f)

    def _crawl(self):
        while Document.crawl(0):
            pass

    def _assertCornerColorEqual(self, img_file, color):
        self.assertTrue(os.path.isfile(img_file))

        with Image.open(img_file) as img:
            rgb = img.getpixel((img.width - 1, img.height - 1))
            self.assertEqual(rgb, color)


class FunctionalTest(BaseFunctionalTest):
    BROWSE_MODE = None

    def _test_preview(self, color=(51, 51, 51)):
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_OGP_URL)
        self.assertEqual(doc.error, '')
        self.assertTrue(doc.has_thumbnail)
        self._assertCornerColorEqual(TEST_SERVER_OGP_THUMBNAIL_FILE, color)

    def test_10_thumbnail_preview(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_PREVIEW,
                                   take_screenshots=False)
        Document.queue(TEST_SERVER_OGP_URL, None, None)
        self._test_preview()

    def test_20_thumbnail_preview_missing(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_PREVIEW,
                                   take_screenshots=False)
        Document.queue(TEST_SERVER_URL, None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL)
        self.assertEqual(doc.error, '')
        self.assertFalse(doc.has_thumbnail)


class BrowserBasedFunctionalTest(BaseFunctionalTest):
    def test_10_thumbnail_screenshot(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_SCREENSHOT,
                                   take_screenshots=False)

        Document.queue(TEST_SERVER_OGP_URL, None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_OGP_URL)
        self.assertEqual(doc.error, '')
        self.assertTrue(doc.has_thumbnail)
        self._assertCornerColorEqual(TEST_SERVER_OGP_THUMBNAIL_FILE, (255, 255, 255))

    def test_20_thumbnail_fallback_preview(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_PREV_OR_SCREEN,
                                   take_screenshots=False)
        Document.queue(TEST_SERVER_OGP_URL, None, None)
        self._test_preview()

    def test_30_thumbnail_fallback_screenshot(self):
        CrawlPolicy.objects.create(url_regex='(default)',
                                   url_regex_pg='.*',
                                   recursion=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=self.BROWSE_MODE,
                                   snapshot_html=False,
                                   thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_PREV_OR_SCREEN,
                                   take_screenshots=False)
        Document.queue(TEST_SERVER_URL, None, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.first()
        self.assertEqual(doc.url, TEST_SERVER_URL)
        self.assertEqual(doc.error, '')
        self.assertTrue(doc.has_thumbnail)
        self._assertCornerColorEqual(TEST_SERVER_THUMBNAIL_FILE, (255, 255, 255))


class RequestsFunctionalTest(FunctionalTest, TransactionTestCase):
    BROWSE_MODE = DomainSetting.BROWSE_REQUESTS
    BROWSER_CLASS = RequestBrowser


class ChromiumFunctionalTest(FunctionalTest, BrowserBasedFunctionalTest, TransactionTestCase):
    BROWSE_MODE = DomainSetting.BROWSE_CHROMIUM
    BROWSER_CLASS = ChromiumBrowser


class FirefoxFunctionalTest(FunctionalTest, BrowserBasedFunctionalTest, TransactionTestCase):
    BROWSE_MODE = DomainSetting.BROWSE_FIREFOX
    BROWSER_CLASS = FirefoxBrowser
