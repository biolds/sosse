# Copyright 2024-2025 Laurent Defert
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

from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

from .collection import Collection


class CollectionTest(TransactionTestCase):
    def setUp(self):
        self.default_policy = Collection.create_default()
        self.policy = Collection.objects.create(name="Test Policy", unlimited_regex="http://127.0.0.1/")

    def test_010_default(self):
        default = Collection.create_default()
        self.assertEqual(self.default_policy, default)

    def test_020_unlimited_regex_parse(self):
        empty = Collection.objects.create(name="Empty Collection", unlimited_regex="# Empty re")
        self.assertEqual(empty.unlimited_regex_pg, "")

        one_re = Collection.objects.create(name="One Regex Collection", unlimited_regex="http://.*")
        self.assertEqual(one_re.unlimited_regex_pg, "http://.*")

        multi_re = Collection.objects.create(name="Multi Regex Collection", unlimited_regex="http://a.*\nhttp://b.*")
        self.assertEqual(multi_re.unlimited_regex_pg, "(http://a.*|http://b.*)")

        other_one_re = Collection.objects.create(
            name="Other Collection",
            limited_regex="http://.*",
            excluded_regex="http://.*",
        )
        self.assertEqual(other_one_re.limited_regex_pg, "http://.*")
        self.assertEqual(other_one_re.excluded_regex_pg, "http://.*")

    def test_030_match(self):
        policy = Collection.get_from_url("http://127.0.0.1/")
        self.assertEqual(policy, self.policy)

    def test_040_no_match(self):
        Collection.get_from_url("# Empty")
        policy = Collection.get_from_url("http://127.0.0.2/")
        self.assertEqual(policy, self.default_policy)

    def test_050_longest_match(self):
        sub_policy = Collection.objects.create(name="Sub Policy Collection", unlimited_regex="http://127.0.0.1/abc/")

        policy = Collection.get_from_url("http://127.0.0.1/abc/plop")
        self.assertEqual(policy, sub_policy)

        policy = Collection.get_from_url("http://127.0.0.1/blah")
        self.assertEqual(policy, self.policy)

        longer = Collection.objects.create(name="Longer Collection", unlimited_regex="http://127.0.0.1/.*")
        policy = Collection.get_from_url("http://127.0.0.1/abc/blah")
        self.assertEqual(policy, longer)

    def test_060_multi_match(self):
        multi = Collection.objects.create(
            name="Multi Match Collection", unlimited_regex="http://127.0.0.1/match1/\nhttp://127.0.0.1/match2/"
        )

        policy = Collection.get_from_url("http://127.0.0.1/match1/url")
        self.assertEqual(policy, multi)

        policy = Collection.get_from_url("http://127.0.0.1/match2/url")
        self.assertEqual(policy, multi)

    def test_070_invalid_regex(self):
        with self.assertRaises(ValidationError):
            policy = Collection(name="Invalid Collection", unlimited_regex="(")
            policy.full_clean()
