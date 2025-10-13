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

from unittest.mock import patch

from django.test import TestCase

from .add_to_queue import AddToQueueForm, _add_unique_patterns
from .collection import Collection
from .document import Document
from .test_views_mixin import ViewsTestMixin


class AddUniquePatternsFunctionTest(TestCase):
    def test_add_to_empty_regex(self):
        result = _add_unique_patterns("", "pattern1\npattern2")
        self.assertEqual(result, "pattern1\npattern2")

    def test_add_to_existing_regex(self):
        existing = "existing1\nexisting2"
        new_patterns = "pattern1\npattern2"
        result = _add_unique_patterns(existing, new_patterns)
        self.assertEqual(result, "existing1\nexisting2\npattern1\npattern2")

    def test_deduplicate_patterns(self):
        existing = "pattern1\npattern2"
        new_patterns = "pattern1\npattern3"
        result = _add_unique_patterns(existing, new_patterns)
        self.assertEqual(result, "pattern1\npattern2\npattern3")

    def test_empty_new_patterns(self):
        existing = "pattern1\npattern2"
        result = _add_unique_patterns(existing, "")
        self.assertEqual(result, "pattern1\npattern2")

    def test_empty_new_patterns_none(self):
        existing = "pattern1\npattern2"
        result = _add_unique_patterns(existing, None)
        self.assertEqual(result, "pattern1\npattern2")

    def test_all_duplicate_patterns(self):
        existing = "pattern1\npattern2"
        new_patterns = "pattern1\npattern2"
        result = _add_unique_patterns(existing, new_patterns)
        self.assertEqual(result, "pattern1\npattern2")

    def test_whitespace_handling(self):
        existing = "pattern1\npattern2"
        new_patterns = " pattern3 \n pattern4 \n\n"
        result = _add_unique_patterns(existing, new_patterns)
        self.assertEqual(result, "pattern1\npattern2\npattern3\npattern4")


class AddToQueueFormTest(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(name="Test Collection")

    def test_form_choices_constants(self):
        self.assertEqual(AddToQueueForm.CRAWL_SCOPE_NO_CHANGE, "no_change")
        self.assertEqual(AddToQueueForm.CRAWL_SCOPE_UNLIMITED, "unlimited")
        self.assertEqual(AddToQueueForm.CRAWL_SCOPE_LIMITED, "limited")

    def test_form_valid_data(self):
        form_data = {
            "urls": "http://example.com\nhttp://test.com",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_NO_CHANGE,
            "show_on_homepage": True,
        }
        form = AddToQueueForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_collection(self):
        form_data = {
            "urls": "http://example.com",
            "collection": 999999,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_NO_CHANGE,
        }
        form = AddToQueueForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_crawl_scope_choices(self):
        form = AddToQueueForm()
        expected_choices = [
            ("no_change", "Keep collection settings unchanged"),
            ("unlimited", "Crawl entire websites (unlimited depth)"),
            ("limited", "Crawl websites with depth limit from collection settings"),
        ]
        self.assertEqual(form.fields["crawl_scope"].choices, expected_choices)

    def test_crawl_scope_default(self):
        form = AddToQueueForm()
        self.assertEqual(form.fields["crawl_scope"].initial, AddToQueueForm.CRAWL_SCOPE_NO_CHANGE)


class AddToQueueViewTest(ViewsTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.collection.unlimited_regex = ""
        self.collection.limited_regex = ""
        self.collection.recursion_depth = 2
        self.collection.save()

    @patch.object(Document, "manual_queue")
    def test_form_valid_no_change(self, mock_queue):
        form_data = {
            "urls": "http://example.com",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_NO_CHANGE,
            "show_on_homepage": False,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 302)

        mock_queue.assert_called_once_with("http://example.com/", self.collection, False)

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.unlimited_regex, "")
        self.assertEqual(self.collection.limited_regex, "")

    @patch.object(Document, "manual_queue")
    def test_form_valid_unlimited_scope(self, mock_queue):
        form_data = {
            "urls": "http://example.com\nhttp://test.com",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_UNLIMITED,
            "show_on_homepage": True,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(mock_queue.call_count, 2)
        mock_queue.assert_any_call("http://example.com/", self.collection, True)
        mock_queue.assert_any_call("http://test.com/", self.collection, True)

        self.collection.refresh_from_db()
        patterns = self.collection.unlimited_regex.split("\n")
        self.assertIn("^https?://example\\.com/.*", patterns)
        self.assertIn("^https?://test\\.com/.*", patterns)
        self.assertEqual(len(patterns), 2)
        self.assertEqual(self.collection.limited_regex, "")

    @patch.object(Document, "manual_queue")
    def test_form_valid_limited_scope(self, mock_queue):
        form_data = {
            "urls": "http://example.com/path",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_LIMITED,
            "show_on_homepage": False,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 302)

        mock_queue.assert_called_once_with("http://example.com/path", self.collection, False)

        self.collection.refresh_from_db()
        expected_pattern = "^https?://example\\.com/.*"
        self.assertEqual(self.collection.limited_regex, expected_pattern)
        self.assertEqual(self.collection.unlimited_regex, "")

    @patch.object(Document, "manual_queue")
    def test_form_valid_existing_patterns(self, mock_queue):
        self.collection.unlimited_regex = "^https?://existing\\.com/.*"
        self.collection.save()

        form_data = {
            "urls": "http://example.com",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_UNLIMITED,
            "show_on_homepage": False,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 302)

        self.collection.refresh_from_db()
        expected_patterns = "^https?://existing\\.com/.*\n^https?://example\\.com/.*"
        self.assertEqual(self.collection.unlimited_regex, expected_patterns)

    @patch.object(Document, "manual_queue")
    def test_form_valid_duplicate_hostnames(self, mock_queue):
        form_data = {
            "urls": "http://example.com/page1\nhttp://example.com/page2",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_UNLIMITED,
            "show_on_homepage": False,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 302)

        self.collection.refresh_from_db()
        expected_pattern = "^https?://example\\.com/.*"
        self.assertEqual(self.collection.unlimited_regex, expected_pattern)

    @patch.object(Document, "manual_queue")
    def test_form_invalid_url(self, mock_queue):
        form_data = {
            "urls": "invalid-url",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_UNLIMITED,
            "show_on_homepage": False,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid URL")

        mock_queue.assert_not_called()

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.unlimited_regex, "")

    @patch.object(Document, "manual_queue")
    def test_form_invalid_relative_url(self, mock_queue):
        form_data = {
            "urls": "/relative/path",
            "collection": self.collection.id,
            "crawl_scope": AddToQueueForm.CRAWL_SCOPE_UNLIMITED,
            "show_on_homepage": False,
        }

        response = self.admin_client.post("/admin/se/document/queue/", form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid URL")

        mock_queue.assert_not_called()

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.unlimited_regex, "")
        self.assertEqual(self.collection.limited_regex, "")

    def test_get_form(self):
        response = self.admin_client.get("/admin/se/document/queue/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="crawl_scope"')
        self.assertContains(response, "Keep collection settings unchanged")
        self.assertContains(response, "Crawl entire websites")
        self.assertContains(response, "Crawl websites with depth limit")
