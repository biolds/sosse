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

import requests
from django.conf import settings
from django.test import TransactionTestCase

from .browser_request import BrowserRequest


class RequestsTest(TransactionTestCase):
    def _get(self, s, url):
        params = BrowserRequest._requests_params()
        params["allow_redirects"] = True
        return s.get(url, **params)

    def test_10_cookie_set(self):
        s = requests.Session()
        self._get(s, "http://127.0.0.1:8000/cookies/set?test_key=test_value")
        cookies = list(s.cookies)
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies[0].name, "test_key")
        self.assertEqual(cookies[0].value, "test_value")
        self.assertEqual(cookies[0].domain, "127.0.0.1")
        return s

    def test_20_cookie_delete(self):
        s = self.test_10_cookie_set()
        self._get(s, "http://127.0.0.1:8000/cookies/delete?test_key")
        cookies = list(s.cookies)
        self.assertEqual(cookies, [])

    def test_30_percent_encoded_url_preserves_case(self):
        # Make sure we don't trigger https://github.com/psf/requests/issues/6473
        URL = "http://127.0.0.1:8000/%e2%82%ac"
        r = BrowserRequest._requests_query("get", URL, settings.SOSSE_MAX_FILE_SIZE)
        self.assertEqual(r.url, URL)

        URL = "http://127.0.0.1:8000/%E2%82%ac"
        r = BrowserRequest._requests_query("get", URL, settings.SOSSE_MAX_FILE_SIZE)
        self.assertEqual(r.url, URL)
