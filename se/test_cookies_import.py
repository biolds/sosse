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

from django.test import TransactionTestCase
from django.utils import timezone

from .cookies_import import CookieForm
from .models import Cookie

NOW = timezone.now().replace(microsecond=0)
NOW_TIMESTAMP = NOW.strftime('%s')


# Cookie format: domain, domain_specified, path, secure, expires, name, value
class CookieImportTest(TransactionTestCase):
    def _load_cookies(self, data):
        if data['format'] == 'netscape':
            data['cookies'] = f'# Netscape HTTP Cookie File\n{data["cookies"]}'

        form = CookieForm(data)
        self.assertTrue(form.is_valid(), form.errors.values())

        cookie_jar = form.cleaned_data['cookies']
        Cookie.set_from_jar(None, cookie_jar)

    def test_010_netscape_simple(self):
        self._load_cookies({
            'cookies': f'.test.com\tTRUE\t/\tFALSE\t{NOW_TIMESTAMP}\tST-n2q1f9\tatbt=CTMQ',
            'format': 'netscape'
        })
        self.assertEqual(Cookie.objects.count(), 1)
        cookie = Cookie.objects.get()
        self.assertEqual(cookie.domain, 'test.com')
        self.assertEqual(cookie.domain_cc, 'test.com')
        self.assertTrue(cookie.inc_subdomain)
        self.assertEqual(cookie.name, 'ST-n2q1f9')
        self.assertEqual(cookie.value, 'atbt=CTMQ')
        self.assertEqual(cookie.path, '/')
        self.assertEqual(cookie.expires, NOW)
        self.assertFalse(cookie.secure)
        self.assertEqual(cookie.same_site, Cookie._meta.get_field('same_site').default)
        self.assertFalse(cookie.http_only)

    def test_020_netscape_httponly(self):
        self._load_cookies({
            'cookies': f'#HttpOnly_.test.com\tTRUE\t/\tFALSE\t{NOW_TIMESTAMP}\tST-n2q1f9\tatbt=CTMQ',
            'format': 'netscape'
        })
        self.assertEqual(Cookie.objects.count(), 1)
        cookie = Cookie.objects.get()
        self.assertEqual(cookie.domain, 'test.com')
        self.assertEqual(cookie.domain_cc, 'test.com')
        self.assertTrue(cookie.inc_subdomain)
        self.assertEqual(cookie.name, 'ST-n2q1f9')
        self.assertEqual(cookie.value, 'atbt=CTMQ')
        self.assertEqual(cookie.path, '/')
        self.assertEqual(cookie.expires, NOW)
        self.assertFalse(cookie.secure)
        self.assertEqual(cookie.same_site, Cookie._meta.get_field('same_site').default)
        self.assertTrue(cookie.http_only)
