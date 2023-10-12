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

from django.test import TransactionTestCase

from .models import Cookie


class SearchTest(TransactionTestCase):
    def setUp(self):
        self.cookie = Cookie.objects.create(domain='test.com',
                                            name='test_name',
                                            value='test_value',
                                            inc_subdomain=False,
                                            secure=False)
        self.cookie_sub = Cookie.objects.create(domain='test2.com',
                                                name='test2_name',
                                                value='test2_value',
                                                inc_subdomain=True,
                                                secure=False)
        self.cookie_secure = Cookie.objects.create(domain='test3.com',
                                                   name='test3_name',
                                                   value='test3_value',
                                                   inc_subdomain=False,
                                                   secure=True)
        self.cookie_path_trail = Cookie.objects.create(domain='test4.com',
                                                       name='test4_name',
                                                       value='test4_value',
                                                       inc_subdomain=False,
                                                       secure=False,
                                                       path='/test/')
        self.cookie_path_no_trail = Cookie.objects.create(domain='test5.com',
                                                          name='test5_name',
                                                          value='test5_value',
                                                          inc_subdomain=False,
                                                          secure=False,
                                                          path='/test')

    def test_domain_no_sub(self):
        self.assertEqual(Cookie.get_from_url('http://test.com/'), [self.cookie])
        self.assertEqual(Cookie.get_from_url('http://test2.com/'), [self.cookie_sub])
        self.assertEqual(Cookie.get_from_url('https://test.com/'), [self.cookie])
        self.assertEqual(Cookie.get_from_url('https://test2.com/'), [self.cookie_sub])

    def test_domain_sub(self):
        self.assertEqual(Cookie.get_from_url('http://www.test.com/'), [])
        self.assertEqual(Cookie.get_from_url('http://www.test2.com/'), [self.cookie_sub])

    def test_secure(self):
        self.assertEqual(Cookie.get_from_url('http://test3.com/'), [])
        self.assertEqual(Cookie.get_from_url('https://test3.com/'), [self.cookie_secure])

    def test_path(self):
        for domain, cookie in (('test4.com', self.cookie_path_trail), ('test5.com', self.cookie_path_no_trail)):
            self.assertEqual(Cookie.get_from_url('http://%s/' % domain), [])
            self.assertEqual(Cookie.get_from_url('http://%s/aaa' % domain), [])
            self.assertEqual(Cookie.get_from_url('http://%s/test' % domain), [cookie])
            self.assertEqual(Cookie.get_from_url('http://%s/test/' % domain), [cookie])
            self.assertEqual(Cookie.get_from_url('http://%s/test/sub' % domain), [cookie])

    def test_set_valid(self):
        c = Cookie.set('http://validcookie.com/', [{'name': 'valid_name', 'value': 'valid_value', 'secure': False}])
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertEqual(c.name, 'valid_name')
        self.assertEqual(c.value, 'valid_value')
        self.assertEqual(c.domain, 'validcookie.com')
        self.assertEqual(c.inc_subdomain, False)

    def test_set_domain(self):
        c = Cookie.set('http://validcookie.com/', [{'name': 'valid_name', 'value': 'valid_value', 'domain': 'validcookie.com', 'secure': False}])
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertEqual(c.name, 'valid_name')
        self.assertEqual(c.value, 'valid_value')
        self.assertEqual(c.domain, 'validcookie.com')
        self.assertEqual(c.inc_subdomain, True)

        c = Cookie.set('http://sub1.validcookie.com/', [{'name': 'valid_name', 'value': 'valid_value', 'domain': 'sub2.validcookie.com', 'secure': False}])
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertEqual(c.name, 'valid_name')
        self.assertEqual(c.value, 'valid_value')
        self.assertEqual(c.domain, 'sub2.validcookie.com')
        self.assertEqual(c.inc_subdomain, True)

    def test_set_invalid(self):
        c = Cookie.set('http://invalidcookie.com/', [{'name': 'valid_name', 'value': 'valid_value', 'domain': 'com', 'secure': False}])
        self.assertEqual(len(c), 0)
        c = Cookie.set('http://invalidcookie.com/', [{'name': 'valid_name', 'value': 'valid_value', 'domain': '.com', 'secure': False}])
        self.assertEqual(len(c), 0)
        c = Cookie.set('http://invalidcookie.com/', [{'name': 'valid_name', 'value': 'valid_value', 'domain': 'test.com', 'secure': False}])
        self.assertEqual(len(c), 0)
        c = Cookie.set('http://com/', [{'name': 'valid_name', 'value': 'valid_value', 'domain': 'com', 'secure': False}])
        self.assertEqual(len(c), 0)
