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
from django.utils import timezone

from ..collection import Collection
from ..document import Document
from .test_rest_api import RestAPITest


class CollectionTest(RestAPITest, TransactionTestCase):
    def test_collection_list(self):
        response = self.client.get("/api/collection/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 2)

        collection_names = [result["name"] for result in data["results"]]
        self.assertEqual(len(collection_names), 2)
        self.assertIn(self.collection.name, collection_names)
        self.assertIn("Test Collection 2", collection_names)

    def test_collection_detail(self):
        response = self.client.get(f"/api/collection/{self.collection.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["id"], self.collection.id)
        self.assertEqual(data["name"], self.collection.name)

    def test_collection_create(self):
        response = self.client.post(
            "/api/collection/",
            {"name": "New Collection", "unlimited_regex": "http://test.com/.*"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "New Collection")
        self.assertEqual(data["unlimited_regex"], "http://test.com/.*")
        self.assertEqual(data["unlimited_regex_pg"], "http://test.com/.*")

    def test_collection_update(self):
        response = self.client.patch(
            f"/api/collection/{self.collection2.id}/",
            {"name": "Updated Collection", "unlimited_regex": "http://updated.com/.*\nhttp://other.com/.*"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "Updated Collection")
        self.assertEqual(data["unlimited_regex"], "http://updated.com/.*\nhttp://other.com/.*")
        self.assertEqual(data["unlimited_regex_pg"], "(http://updated.com/.*|http://other.com/.*)")

    def test_collection_delete(self):
        new_collection = Collection.objects.create(name="To Delete", unlimited_regex="http://delete.com/.*")
        response = self.client.delete(f"/api/collection/{new_collection.id}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(Collection.objects.filter(id=new_collection.id).exists())

    def test_collection_create_with_tags_webhooks(self):
        response = self.client.post(
            "/api/collection/",
            {
                "name": "Collection with Relations",
                "unlimited_regex": "http://test.com/.*",
                "tags": [self.tag.id, self.subtag.id],
                "webhooks": [self.test_webhook.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "Collection with Relations")
        self.assertEqual(sorted(data["tags"]), sorted([self.tag.id, self.subtag.id]))
        self.assertEqual(data["webhooks"], [self.test_webhook.id])

    def test_collection_update_tags_webhooks(self):
        response = self.client.patch(
            f"/api/collection/{self.collection2.id}/",
            {"tags": [self.subtag.id], "webhooks": [self.test_webhook.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["tags"], [self.subtag.id])
        self.assertEqual(data["webhooks"], [self.test_webhook.id])

    def test_collection_detail_statistics(self):
        now = timezone.now()
        crawl_first_time = now - timezone.timedelta(days=10)
        crawl_last_time = now - timezone.timedelta(days=1)
        crawl_next_time = now + timezone.timedelta(days=1)

        Document.objects.wo_content().create(
            url="http://127.0.0.1/robots_rejected",
            normalized_url="http test robots",
            title="Robots Rejected",
            normalized_title="robots rejected",
            content="Content",
            normalized_content="content",
            crawl_first=crawl_first_time,
            crawl_last=crawl_last_time,
            crawl_next=crawl_next_time,
            robotstxt_rejected=True,
            collection=self.collection,
        )

        Document.objects.wo_content().create(
            url="http://127.0.0.1/with_error",
            normalized_url="http test error",
            title="With Error",
            normalized_title="with error",
            content="Content",
            normalized_content="content",
            crawl_first=crawl_first_time,
            crawl_last=now,
            crawl_next=now + timezone.timedelta(days=2),
            error="Some error message",
            collection=self.collection,
        )

        response = self.client.get(f"/api/collection/{self.collection.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)

        self.assertEqual(data["documents_count"], 4)
        self.assertEqual(data["robotstxt_rejected"], 1)
        self.assertEqual(data["errors"], 1)
        self.assertIsNotNone(data["crawl_first"])
        self.assertIsNotNone(data["crawl_last"])
        self.assertIsNotNone(data["crawl_next"])
