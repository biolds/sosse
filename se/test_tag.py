# Copyright 2025 Laurent Defert
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

from django.test import TransactionTestCase

from .document import Document
from .search import add_query_param, remove_query_param
from .tag import Tag
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

    def test_tree_doc_counts(self):
        # Create some tags and documents
        tag1 = Tag.objects.create(name="Tag 1")
        tag2 = Tag.objects.create(name="Tag 2", parent=tag1)
        tag3 = Tag.objects.create(name="Tag 3")
        tag4 = Tag.objects.create(name="Tag 4", parent=tag3)

        doc1 = Document.objects.create(url="http://example.com/doc1", collection=self.collection)
        doc1.tags.add(tag1)
        doc2 = Document.objects.create(url="http://example.com/doc2", collection=self.collection)
        doc2.tags.add(tag2)
        doc3 = Document.objects.create(url="http://example.com/doc3", collection=self.collection)
        doc3.tags.set([tag3, tag4])

        doc_counts = Tag.tree_doc_counts()
        self.assertEqual(
            doc_counts,
            {
                tag1.pk: {"count": 2, "human_count": "2"},
                tag2.pk: {"count": 1, "human_count": "1"},
                tag3.pk: {"count": 1, "human_count": "1"},
                tag4.pk: {"count": 1, "human_count": "1"},
            },
        )
