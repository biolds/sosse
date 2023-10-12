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

import requests

from django.test import TransactionTestCase

from .browser import RequestBrowser


class RequestsTest(TransactionTestCase):
    def _get(self, s, url):
        params = RequestBrowser._requests_params()
        params['allow_redirects'] = True
        return s.get(url, **params)

    def test_10_cookie_set(self):
        s = requests.Session()
        self._get(s, 'http://127.0.0.1:8000/cookies/set?test_key=test_value')
        cookies = list(s.cookies)
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies[0].name, 'test_key')
        self.assertEqual(cookies[0].value, 'test_value')
        self.assertEqual(cookies[0].domain, '127.0.0.1')
        return s

    def test_20_cookie_delete(self):
        s = self.test_10_cookie_set()
        self._get(s, 'http://127.0.0.1:8000/cookies/delete?test_key')
        cookies = list(s.cookies)
        self.assertEqual(cookies, [])
