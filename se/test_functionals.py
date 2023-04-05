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

from .browser import Browser
from .models import Cookie, CrawlPolicy, Document, DomainSetting, Link


TEST_SERVER_URL = 'http://127.0.0.1:8000/'


class SimpleTest(TestCase):
    def setUp(self):
        Browser.init()

    def _crawl(self):
        Document.queue(TEST_SERVER_URL, None, None)
        while Document.crawl(0):
            pass

    def _check(self):
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

    def test_10_requests(self):
        CrawlPolicy.objects.create(url_regex='.*',
                                   condition=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=DomainSetting.BROWSE_REQUESTS)
        self._crawl()
        self._check()

    def test_20_selenium(self):
        CrawlPolicy.objects.create(url_regex='.*',
                                   condition=CrawlPolicy.CRAWL_NEVER,
                                   recrawl_mode=CrawlPolicy.RECRAWL_NONE,
                                   default_browse_mode=DomainSetting.BROWSE_SELENIUM)
        self._crawl()
        self._check()
