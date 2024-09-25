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

from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

from .models import CrawlPolicy


class CrawlPolicyTest(TransactionTestCase):
    def setUp(self):
        self.default_policy = CrawlPolicy.create_default()
        self.policy = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/')

    def test_010_default(self):
        default = CrawlPolicy.create_default()
        self.assertEqual(self.default_policy, default)

    def test_020_url_regex_parse(self):
        empty = CrawlPolicy.objects.create(url_regex='# Empty re')
        self.assertEqual(empty.url_regex_pg, '')

        one_re = CrawlPolicy.objects.create(url_regex='http://.*')
        self.assertEqual(one_re.url_regex_pg, 'http://.*')

        multi_re = CrawlPolicy.objects.create(url_regex='http://a.*\nhttp://b.*')
        self.assertEqual(multi_re.url_regex_pg, '(http://a.*|http://b.*)')

    def test_030_match(self):
        policy = CrawlPolicy.get_from_url('http://127.0.0.1/')
        self.assertEqual(policy, self.policy)

    def test_040_no_match(self):
        CrawlPolicy.get_from_url('# Empty')
        policy = CrawlPolicy.get_from_url('http://127.0.0.2/')
        self.assertEqual(policy, self.default_policy)

    def test_050_longest_match(self):
        sub_policy = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/abc/')

        policy = CrawlPolicy.get_from_url('http://127.0.0.1/abc/plop')
        self.assertEqual(policy, sub_policy)

        policy = CrawlPolicy.get_from_url('http://127.0.0.1/blah')
        self.assertEqual(policy, self.policy)

        longer = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/.*')
        policy = CrawlPolicy.get_from_url('http://127.0.0.1/abc/blah')
        self.assertEqual(policy, longer)

    def test_060_multi_match(self):
        multi = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/match1/\nhttp://127.0.0.1/match2/')

        policy = CrawlPolicy.get_from_url('http://127.0.0.1/match1/url')
        self.assertEqual(policy, multi)

        policy = CrawlPolicy.get_from_url('http://127.0.0.1/match2/url')
        self.assertEqual(policy, multi)

    def test_070_invalid_regex(self):
        with self.assertRaises(ValidationError):
            policy = CrawlPolicy(url_regex='(')
            policy.full_clean()
