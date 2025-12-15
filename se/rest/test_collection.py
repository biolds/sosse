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

from ..collection import Collection
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
