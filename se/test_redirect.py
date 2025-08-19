# Copyright 2022-2025 Laurent Defert
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

from django.test import TransactionTestCase

from .browser import SkipIndexing
from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .browser_request import BrowserRequest
from .collection import Collection
from .test_mock import CleanTest, FirefoxTest

TEST_SERVER_URL = "http://127.0.0.1:8000/"


class RedirectTest:
    def setUp(self):
        self.collection = Collection.create_default()

    @classmethod
    def tearDownClass(cls):
        BrowserChromium.destroy()
        BrowserFirefox.destroy()

    def test_10_no_redirect(self):
        page = self.BROWSER.get(TEST_SERVER_URL, self.collection)
        self.assertEqual(page.url, TEST_SERVER_URL)
        self.assertEqual(page.redirect_count, 0)
        self.assertIn(b"This page.", page.content)

    def test_20_one_redirect(self):
        page = self.BROWSER.get(TEST_SERVER_URL + "redirect/1", self.collection)
        self.assertEqual(page.url, TEST_SERVER_URL + "get")
        self.assertEqual(page.redirect_count, 1)
        self._check_key_val("url", '"http://127.0.0.1:8000/get"', page.content)


class RequestsRedirectTest(RedirectTest, CleanTest, TransactionTestCase):
    BROWSER = BrowserRequest

    def test_30_five_redirects(self):
        page = self.BROWSER.get(TEST_SERVER_URL + "redirect/5", self.collection)
        self.assertEqual(page.url, TEST_SERVER_URL + "get")
        self.assertEqual(page.redirect_count, 5)
        self.assertIn(b'"url": "http://127.0.0.1:8000/get"', page.content)

    def test_40_max_redirect(self):
        with self.assertRaises(SkipIndexing):
            self.BROWSER.get(TEST_SERVER_URL + "redirect/6", self.collection)


class FirefoxRedirectTest(RedirectTest, FirefoxTest, TransactionTestCase):
    BROWSER = BrowserFirefox


class ChromiumRedirectTest(RedirectTest, CleanTest, TransactionTestCase):
    BROWSER = BrowserChromium
