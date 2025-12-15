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

from ..tag import Tag
from .test_rest_api import SERIALIZED_DOC1, RestAPITest


class DocumentTest(RestAPITest, TransactionTestCase):
    def test_document_list(self):
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["next"], None)
        self.assertEqual(data["previous"], None)

        doc_ids = [result["id"] for result in data["results"]]
        self.assertIn(self.doc1.id, doc_ids)
        self.assertIn(self.doc2.id, doc_ids)
        self.assertIn(self.doc3.id, doc_ids)

    def test_document_detail(self):
        response = self.client.get(f"/api/document/{self.doc1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content), SERIALIZED_DOC1 | {"id": self.doc1.id, "collection": self.collection.id}
        )

    def test_document_tags_str_update(self):
        response = self.client.patch(
            f"/api/document/{self.doc1.id}/", {"tags": ["tag1", "tag2"]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.doc1.refresh_from_db()
        tags = list(self.doc1.tags.values_list("name", flat=True))
        self.assertEqual(tags, ["tag1", "tag2"])

    def test_document_tags_pk_update(self):
        tag = Tag.objects.create(name="test tag")
        response = self.client.patch(
            f"/api/document/{self.doc1.id}/", {"tags": [tag.pk]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.doc1.refresh_from_db()
        tags = list(self.doc1.tags.values_list("name", flat=True))
        self.assertEqual(tags, ["test tag"])

    def test_document_normalize(self):
        response = self.client.patch(
            f"/api/document/{self.doc1.id}/", {"title": "tïtle", "content": "contènt"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.normalized_title, "title")
        self.assertEqual(self.doc1.normalized_content, "content")

    def test_document_create_prohibited(self):
        response = self.client.post("/api/document/", {"url": "http://127.0.0.1/"}, content_type="application/json")
        self.assertEqual(response.status_code, 405, response.content)
