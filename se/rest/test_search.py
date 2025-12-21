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

from .test_rest_api import (
    SERIALIZED_DOC1_BASE,
    SERIALIZED_DOC2_BASE,
    SERIALIZED_DOC3_BASE,
    RestAPITest,
)


class SearchTest(RestAPITest, TransactionTestCase):
    def test_search(self):
        response = self.client.post("/api/search/", {"query": "content"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC1_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc1.id,
                        "score": 0.12158542,
                        "headline": '<span class="search-highlight">Content</span>',
                        "snapshot_url": None,
                    }
                ],
            },
        )

    def test_search_has_params(self):
        response = self.client.post("/api/search/", {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content),
            {"non_field_errors": ['At least "query" or "adv_params" field must be provided.']},
        )

    def test_search_title(self):
        response = self.client.post(
            "/api/search/",
            {"adv_params": [{"field": "content", "term": "Content2"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC2_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 1.0,
                        "headline": "Other Content2",
                        "tag_list": [SERIALIZED_DOC2_BASE["tag_list"][0] | {"id": self.subtag.id}],
                    }
                ],
            },
        )

    def test_search_hidden(self):
        self.doc2.hidden = True
        self.doc2.save()

        response = self.client.post("/api/search/", {"query": "http"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC1_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc1.id,
                        "score": 0.6079271,
                        "headline": "Content",
                    },
                    SERIALIZED_DOC3_BASE
                    | {
                        "collection": self.collection2.id,
                        "id": self.doc3.id,
                        "score": 0.6079271,
                        "headline": "Content3",
                    },
                ],
            },
        )

    def test_search_hidden_included(self):
        self.doc2.hidden = True
        self.doc2.save()

        response = self.client.post("/api/search/", {"query": "http", "include_hidden": True})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC1_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc1.id,
                        "score": 0.6079271,
                        "headline": "Content",
                    },
                    SERIALIZED_DOC2_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 0.6079271,
                        "hidden": True,
                        "headline": "Other Content2",
                        "tag_list": [SERIALIZED_DOC2_BASE["tag_list"][0] | {"id": self.subtag.id}],
                    },
                    SERIALIZED_DOC3_BASE
                    | {
                        "collection": self.collection2.id,
                        "id": self.doc3.id,
                        "score": 0.6079271,
                        "headline": "Content3",
                    },
                ],
            },
        )

    def test_search_tags(self):
        response = self.client.post(
            "/api/search/",
            {"adv_params": [{"field": "tag", "term": "Sub Tag", "operator": "equal"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC2_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 1.0,
                        "headline": "Other Content2",
                        "tag_list": [SERIALIZED_DOC2_BASE["tag_list"][0] | {"id": self.subtag.id}],
                    },
                ],
            },
        )

    def test_search_subtags(self):
        response = self.client.post(
            "/api/search/",
            {"adv_params": [{"field": "tag", "term": "Group", "operator": "equal"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC2_BASE
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 1.0,
                        "headline": "Other Content2",
                        "tag_list": [SERIALIZED_DOC2_BASE["tag_list"][0] | {"id": self.subtag.id}],
                    },
                ],
            },
        )

    def test_search_collection_filter(self):
        response = self.client.post("/api/search/", {"query": "content", "collection": self.collection.id})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.doc1.id)

    def test_search_collection_filter_different(self):
        response = self.client.post("/api/search/", {"query": "content3", "collection": self.collection2.id})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.doc3.id)

    def test_search_no_collection_filter(self):
        response = self.client.post("/api/search/", {"query": "http"})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        doc_ids = [result["id"] for result in data["results"]]
        self.assertIn(self.doc1.id, doc_ids)
        self.assertIn(self.doc2.id, doc_ids)
        self.assertIn(self.doc3.id, doc_ids)

    def test_search_collection_nonexistent(self):
        response = self.client.post("/api/search/", {"query": "content", "collection": 99999})
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("Collection with id 99999 does not exist", data["collection"][0])
