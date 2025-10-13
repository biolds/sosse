# Copyright 2024-2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import os
from hashlib import md5

from django.conf import settings
from django.test import TransactionTestCase
from PIL import Image

from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .browser_request import BrowserRequest
from .collection import Collection
from .document import Document
from .domain import Domain

TEST_SERVER_DOMAIN = "127.0.0.1:8000"
TEST_SERVER_URL = f"http://{TEST_SERVER_DOMAIN}/"
TEST_SERVER_URL_MD5 = md5(TEST_SERVER_URL.encode("utf-8")).hexdigest()
TEST_SERVER_THUMBNAIL_FILE = (
    os.path.join(settings.SOSSE_THUMBNAILS_DIR, TEST_SERVER_URL_MD5[:2], TEST_SERVER_URL_MD5) + ".jpg"
)

TEST_SERVER_OGP_URL = f"{TEST_SERVER_URL}ogp/"
TEST_SERVER_OGP_URL_MD5 = md5(TEST_SERVER_OGP_URL.encode("utf-8")).hexdigest()
TEST_SERVER_OGP_THUMBNAIL_FILE = (
    os.path.join(
        settings.SOSSE_THUMBNAILS_DIR,
        TEST_SERVER_OGP_URL_MD5[:2],
        TEST_SERVER_OGP_URL_MD5,
    )
    + ".jpg"
)


class BaseFunctionalTest:
    @classmethod
    def tearDownClass(cls):
        BrowserChromium.destroy()
        BrowserFirefox.destroy()

    def setUp(self):
        self.assertEqual(Document.objects.count(), 0)
        self.collection = Collection.objects.create(
            name="Test Collection",
            unlimited_regex="",
            unlimited_regex_pg="",
            recrawl_freq=Collection.RECRAWL_FREQ_NONE,
            default_browse_mode=self.BROWSE_MODE,
            snapshot_html=False,
            thumbnail_mode=Collection.THUMBNAIL_MODE_PREVIEW,
            take_screenshots=False,
        )

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

        doc = Document.objects.w_content().first()
        self.assertEqual(doc.url, TEST_SERVER_OGP_URL)
        self.assertEqual(doc.error, "")
        self.assertTrue(doc.has_thumbnail)
        self._assertCornerColorEqual(TEST_SERVER_OGP_THUMBNAIL_FILE, color)

    def test_10_thumbnail_preview(self):
        self.collection.thumbnail_mode = Collection.THUMBNAIL_MODE_PREVIEW
        self.collection.save()
        Document.queue(TEST_SERVER_OGP_URL, self.collection, None)
        self._test_preview()

    def test_20_thumbnail_preview_missing(self):
        self.collection.thumbnail_mode = Collection.THUMBNAIL_MODE_PREVIEW
        self.collection.save()
        Document.queue(TEST_SERVER_URL, self.collection, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, TEST_SERVER_URL)
        self.assertEqual(doc.error, "")
        self.assertFalse(doc.has_thumbnail)


class BrowserBasedFunctionalTest(BaseFunctionalTest):
    def test_10_thumbnail_screenshot(self):
        self.collection.thumbnail_mode = Collection.THUMBNAIL_MODE_SCREENSHOT
        self.collection.save()

        Document.queue(TEST_SERVER_OGP_URL, self.collection, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().first()
        self.assertEqual(doc.url, TEST_SERVER_OGP_URL)
        self.assertEqual(doc.error, "")
        self.assertTrue(doc.has_thumbnail)
        self._assertCornerColorEqual(TEST_SERVER_OGP_THUMBNAIL_FILE, (255, 255, 255))

    def test_20_thumbnail_fallback_preview(self):
        self.collection.thumbnail_mode = Collection.THUMBNAIL_MODE_PREV_OR_SCREEN
        self.collection.save()
        Document.queue(TEST_SERVER_OGP_URL, self.collection, None)
        self._test_preview()

    def test_30_thumbnail_fallback_screenshot(self):
        self.collection.thumbnail_mode = Collection.THUMBNAIL_MODE_PREV_OR_SCREEN
        self.collection.save()
        Document.queue(TEST_SERVER_URL, self.collection, None)
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().first()
        self.assertEqual(doc.url, TEST_SERVER_URL)
        self.assertEqual(doc.error, "")
        self.assertTrue(doc.has_thumbnail)
        self._assertCornerColorEqual(TEST_SERVER_THUMBNAIL_FILE, (255, 255, 255))


class RequestsFunctionalTest(FunctionalTest, TransactionTestCase):
    BROWSE_MODE = Domain.BROWSE_REQUESTS
    BROWSER_CLASS = BrowserRequest


class ChromiumFunctionalTest(FunctionalTest, BrowserBasedFunctionalTest, TransactionTestCase):
    BROWSE_MODE = Domain.BROWSE_CHROMIUM
    BROWSER_CLASS = BrowserChromium


class FirefoxFunctionalTest(FunctionalTest, BrowserBasedFunctionalTest, TransactionTestCase):
    BROWSE_MODE = Domain.BROWSE_FIREFOX
    BROWSER_CLASS = BrowserFirefox
