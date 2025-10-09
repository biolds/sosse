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

import json
from io import StringIO

from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils.timezone import now

from .collection import Collection
from .document import Document
from .models import WorkerStats


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


class QueueStatusCommandTest(TransactionTestCase):
    def setUp(self):
        self.collection = Collection.create_default()
        self.current_time = now()

    def test_queue_status_text_format(self):
        """Test queue_status command with text output format."""
        # Create test data
        Document.objects.wo_content().create(url="http://new.test/", collection=self.collection)
        Document.objects.wo_content().create(url="http://processing.test/", collection=self.collection, worker_no=0)
        WorkerStats.objects.create(worker_no=0, pid=12345, state="idle", doc_processed=5)

        out = StringIO()
        call_command("queue_status", stdout=out)
        output = out.getvalue()

        # Verify basic structure
        self.assertIn("=== Crawling Queue Status ===", output)
        self.assertIn("Queue:", output)
        self.assertIn("Workers", output)
        self.assertIn("Documents being processed: 1", output)
        self.assertIn("New documents pending: 1", output)
        self.assertIn("Worker 0:", output)

    def test_queue_status_json_format(self):
        """Test queue_status command with JSON output format."""
        # Create test data
        Document.objects.wo_content().create(url="http://new.test/", collection=self.collection)
        WorkerStats.objects.create(worker_no=0, pid=12345, state="idle", doc_processed=5)

        out = StringIO()
        call_command("queue_status", "--format", "json", stdout=out)
        output = out.getvalue()

        # Parse and verify JSON structure
        data = json.loads(output)

        self.assertIn("timestamp", data)
        self.assertIn("queue", data)
        self.assertIn("workers", data)

        # Verify queue data
        queue_data = data["queue"]
        self.assertEqual(queue_data["processing"], 0)
        self.assertEqual(queue_data["new"], 1)
        self.assertEqual(queue_data["recurring"], 0)
        self.assertEqual(queue_data["total_pending"], 1)

        # Verify workers data structure
        workers_data = data["workers"]
        self.assertEqual(workers_data["count"], 1)
        self.assertEqual(len(workers_data["details"]), 1)

        worker_detail = workers_data["details"][0]
        self.assertEqual(worker_detail["worker_no"], 0)
        self.assertIn("pid", worker_detail)
        self.assertIn("state", worker_detail)
        self.assertEqual(worker_detail["doc_processed"], 5)
