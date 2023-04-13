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

from se.models import DomainSetting


ROBOTS_TXT = '''
# Test robots.txt
user-agent: *
allow: /allow/*
disallow: /disallow/*
'''


class MiscTest(TestCase):
    def test_robots_txt(self):
        domain = DomainSetting.objects.create(domain='127.0.0.1')
        domain._parse_robotstxt(ROBOTS_TXT)
        self.assertEqual(domain.robots_allow, '/allow/.*')
        self.assertEqual(domain.robots_disallow, '/disallow/.*')

        domain.robots_ua_hash = DomainSetting.ua_hash()
        domain.robots_status = DomainSetting.ROBOTS_LOADED
        domain.save()

        self.assertTrue(domain.robots_authorized('http://127.0.0.1/allow/aa'))
        self.assertFalse(domain.robots_authorized('http://127.0.0.1/disallow/aa'))
