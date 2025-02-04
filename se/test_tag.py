# Copyright 2025 Laurent Defert
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

from .search import add_query_param, remove_query_param
from .test_views_mixin import ViewsTestMixin


class TagTest(ViewsTestMixin, TransactionTestCase):
    def test_remove_query_param(self):
        request = self._request_from_factory("/?a=1&b=2&c=3", None)
        self.assertEqual(remove_query_param(request, "a", "1"), "/?b=2&c=3")

    def test_remove_query_param_multi(self):
        request = self._request_from_factory("/?a=1&a=2&c=3", None)
        self.assertEqual(remove_query_param(request, "a", "1"), "/?a=2&c=3")
        request = self._request_from_factory("/?a=1&a=2&a=3", None)
        self.assertEqual(remove_query_param(request, "a", "1"), "/?a=2&a=3")

    def test_remove_query_param_absent(self):
        request = self._request_from_factory("/?b=2&c=3", None)
        self.assertEqual(remove_query_param(request, "a", "1"), "/?b=2&c=3")

    def test_remove_query_param_no_value(self):
        request = self._request_from_factory("/?a=1&a=2&c=3", None)
        self.assertEqual(remove_query_param(request, "a"), "/?c=3")

    def test_add_query_param(self):
        request = self._request_from_factory("/?b=2&c=3", None)
        self.assertEqual(add_query_param(request, "a", "1"), "/?b=2&c=3&a=1")

    def test_add_query_param_multi(self):
        request = self._request_from_factory("/?b=2&c=3", None)
        self.assertEqual(add_query_param(request, "b", "1"), "/?b=2&b=1&c=3")
