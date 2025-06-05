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

from django.test import TransactionTestCase, override_settings

from .document import Document
from .domain_setting import DomainSetting

ROBOTS_TXT = """
# Test robots.txt
user-agent: *
allow: /allow/*
disallow: /disallow/*
"""


class MiscTest(TransactionTestCase):
    def test_robots_txt(self):
        domain = DomainSetting.objects.create(domain="127.0.0.1")
        domain._parse_robotstxt(ROBOTS_TXT)
        self.assertEqual(domain.robots_allow, "/allow/.*")
        self.assertEqual(domain.robots_disallow, "/disallow/.*")

        domain.robots_ua_hash = DomainSetting.ua_hash()
        domain.robots_status = DomainSetting.ROBOTS_LOADED
        domain.save()

        self.assertTrue(domain.robots_authorized("http://127.0.0.1/allow/aa"))
        self.assertFalse(domain.robots_authorized("http://127.0.0.1/disallow/aa"))

    @override_settings(SOSSE_LINKS_NO_REFERRER=True)
    @override_settings(SOSSE_LINKS_NEW_TAB=True)
    def test_external_link(self):
        doc = Document(url="http://test/")
        self.assertEqual(
            doc.get_source_link(),
            '🌍&nbsp<a href="http://test/" rel="noreferrer" target="_blank">Source</a>',
        )

    @override_settings(SOSSE_LINKS_NO_REFERRER=False)
    @override_settings(SOSSE_LINKS_NEW_TAB=False)
    def test_external_link_no_opt(self):
        doc = Document(url="http://test/")
        self.assertEqual(doc.get_source_link(), '🌍&nbsp<a href="http://test/">Source</a>')
