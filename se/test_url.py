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

from .models import absolutize_url


class UrlTest(TestCase):
    def test_absolutize(self):
        self.assertEqual(absolutize_url('http://127.0.0.1/', 'http://127.0.0.2/', True, True), 'http://127.0.0.2/')
        self.assertEqual(absolutize_url('http://127.0.0.1/', 'page.html', True, True), 'http://127.0.0.1/page.html')
        self.assertEqual(absolutize_url('http://127.0.0.1/dir1/', '/page.html', True, True), 'http://127.0.0.1/page.html')
        self.assertEqual(absolutize_url('http://127.0.0.1/dir1/dir2/', '../page.html', True, True), 'http://127.0.0.1/dir1/page.html')

    def test_no_scheme(self):
        self.assertEqual(absolutize_url('http://127.0.0.1/', '//127.0.0.2/', True, True), 'http://127.0.0.2/')
        self.assertEqual(absolutize_url('https://127.0.0.1/', '//127.0.0.2/', True, True), 'https://127.0.0.2/')

    def test_rel(self):
        self.assertEqual(absolutize_url('http://127.0.0.1/', './page.html', True, True), 'http://127.0.0.1/page.html')
        self.assertEqual(absolutize_url('https://127.0.0.1/index.html', './page.html', True, True), 'https://127.0.0.1/page.html')

    def test_params(self):
        self.assertEqual(absolutize_url('http://127.0.0.1/index.html?f=1', './page.html?g=3', True, True), 'http://127.0.0.1/page.html?g=3')
