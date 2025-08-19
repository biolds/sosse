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

from .archive import ArchiveMixin
from .collection import Collection
from .document import Document
from .test_views_mixin import ViewsTestMixin


class TestArchiveMixin(ArchiveMixin):
    """Test class that inherits from ArchiveMixin for testing purposes."""

    view_name = "test_view"


class ArchiveMixinTest(ViewsTestMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.test_url = "https://example.com/test/page"

        # Create a second collection for testing
        self.collection2 = Collection.objects.create(name="Test Collection 2", unlimited_regex="https://example.com/.*")

        # Create documents in different collections
        self.doc1 = Document.objects.create(
            url=self.test_url, title="Test Document 1", collection=self.collection, content="Test content 1"
        )

        self.doc2 = Document.objects.create(
            url=self.test_url, title="Test Document 2", collection=self.collection2, content="Test content 2"
        )

    def test_get_document_without_collection_in_url(self):
        """Test that _get_document returns the first document when no
        collection is specified in URL."""
        # Create a request without collection ID in the path
        request = self.factory.get(f"/www/{self.test_url}")
        request.META["REQUEST_URI"] = f"/www/{self.test_url}"

        mixin = TestArchiveMixin()
        mixin.request = request

        # Should return the first document (ordered by id)
        doc = mixin._get_document()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.id, self.doc1.id)
        self.assertEqual(doc.title, "Test Document 1")
        self.assertIsNone(mixin.collection_id)
        self.assertIsNone(mixin.collection)

    def test_get_document_with_collection_in_url(self):
        """Test that _get_document returns the document from the specified
        collection when collection ID is in URL."""
        # Create a request with collection ID in the path
        request = self.factory.get(f"/www/{self.collection2.id}/{self.test_url}")
        request.META["REQUEST_URI"] = f"/www/{self.collection2.id}/{self.test_url}"

        mixin = TestArchiveMixin()
        mixin.request = request

        # Should return the document from collection2
        doc = mixin._get_document()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.id, self.doc2.id)
        self.assertEqual(doc.title, "Test Document 2")
        self.assertEqual(doc.collection, self.collection2)
        self.assertEqual(mixin.collection_id, self.collection2.id)
        self.assertEqual(mixin.collection, self.collection2)
