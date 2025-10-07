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

from django.core.management import call_command
from django.test import TransactionTestCase

from .collection import Collection
from .document import Document


class CommandsTest(TransactionTestCase):
    def setUp(self):
        self.collection = Collection.create_default()
        Document.objects.wo_content().create(url="http://test/", collection=self.collection)

    def test_delete_document_match(self):
        self.assertEqual(Document.objects.count(), 1)
        call_command("delete_documents", "http://test")
        self.assertEqual(Document.objects.count(), 0)

    def test_delete_document_no_match(self):
        self.assertEqual(Document.objects.count(), 1)
        call_command("delete_documents", "http://no_test")
        self.assertEqual(Document.objects.count(), 1)

    def test_delete_document_dry_run(self):
        self.assertEqual(Document.objects.count(), 1)
        with self.assertRaises(SystemExit):
            call_command("delete_documents", "--dry-run", "http://test")
        self.assertEqual(Document.objects.count(), 1)

    def test_delete_document_exclude(self):
        # Create additional documents for exclusion test
        Document.objects.wo_content().create(url="http://test/important.html", collection=self.collection)
        Document.objects.wo_content().create(url="http://test/regular.html", collection=self.collection)
        self.assertEqual(Document.objects.wo_content().count(), 3)

        # Delete all test documents except those containing "important"
        call_command("delete_documents", "http://test", "--exclude", "important")

        # Should only have the important document left
        self.assertEqual(Document.objects.wo_content().count(), 1)
        remaining_doc = Document.objects.wo_content().first()
        self.assertIn("important", remaining_doc.url)

    def test_delete_document_ignore_case(self):
        # Create documents with different cases
        Document.objects.wo_content().create(url="http://TEST/page.html", collection=self.collection)
        Document.objects.wo_content().create(url="http://other/page.html", collection=self.collection)
        self.assertEqual(Document.objects.wo_content().count(), 3)

        # Delete with ignore case - should match both "test" and "TEST"
        call_command("delete_documents", "test", "--ignore-case")

        # Should only have the "other" document left
        self.assertEqual(Document.objects.wo_content().count(), 1)
        remaining_doc = Document.objects.wo_content().first()
        self.assertIn("other", remaining_doc.url)
