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

import json

from django.test import TransactionTestCase

from ..document import Document
from .test_rest_api import RestAPITest


class AddToQueueTest(RestAPITest, TransactionTestCase):
    def test_queue_urls_basic(self):
        initial_count = Document.objects.count()
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://newsite.com/page1", "http://newsite.com/page2"],
                "collection": self.collection.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["message"], "2 URLs queued successfully")
        self.assertEqual(len(data["queued_urls"]), 2)
        self.assertIn("http://newsite.com/page1", data["queued_urls"])
        self.assertIn("http://newsite.com/page2", data["queued_urls"])
        self.assertEqual(data["collection"], self.collection.id)
        self.assertEqual(Document.objects.count(), initial_count + 2)

    def test_queue_urls_unlimited_scope(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://newsite.com/page"],
                "collection": self.collection.id,
                "crawl_scope": "unlimited",
                "show_on_homepage": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["crawl_scope"], "unlimited")
        self.assertEqual(data["show_on_homepage"], False)

        self.collection.refresh_from_db()
        self.assertIn("^https?://newsite\\.com/.*", self.collection.unlimited_regex)

    def test_queue_urls_limited_scope(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://testsite.org/"],
                "collection": self.collection.id,
                "crawl_scope": "limited",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        self.collection.refresh_from_db()
        self.assertIn("^https?://testsite\\.org/.*", self.collection.limited_regex)

    def test_queue_urls_invalid_url(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["not-a-valid-url", "http://valid.com"],
                "collection": self.collection.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("urls", data)

    def test_queue_urls_nonexistent_collection(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://test.com"],
                "collection": 99999,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("collection", data)
