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

from ..cookie import Cookie
from .test_rest_api import RestAPITest


class BulkActionMixinTest(RestAPITest, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.cookie1 = Cookie.objects.create(
            domain="example.com",
            name="session_id",
            value="abc123",
            path="/",
            inc_subdomain=False,
            secure=False,
        )
        self.cookie2 = Cookie.objects.create(
            domain="test.com",
            name="auth_token",
            value="xyz789",
            path="/api",
            inc_subdomain=True,
            secure=True,
        )
        self.cookie3 = Cookie.objects.create(
            domain="example.org",
            name="tracking",
            value="tracking123",
            path="/",
            inc_subdomain=False,
            secure=False,
        )

    def test_bulk_action_delete_single(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "delete", "ids": [self.cookie1.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["deleted"], 1)
        self.assertFalse(Cookie.objects.filter(id=self.cookie1.id).exists())
        self.assertTrue(Cookie.objects.filter(id=self.cookie2.id).exists())
        self.assertTrue(Cookie.objects.filter(id=self.cookie3.id).exists())

    def test_bulk_action_delete_multiple(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "delete", "ids": [self.cookie1.id, self.cookie2.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["deleted"], 2)
        self.assertFalse(Cookie.objects.filter(id=self.cookie1.id).exists())
        self.assertFalse(Cookie.objects.filter(id=self.cookie2.id).exists())
        self.assertTrue(Cookie.objects.filter(id=self.cookie3.id).exists())

    def test_bulk_action_delete_all(self):
        response = self.client.post(
            "/api/cookie/action/",
            {
                "action": "delete",
                "ids": [self.cookie1.id, self.cookie2.id, self.cookie3.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["deleted"], 3)
        self.assertEqual(Cookie.objects.count(), 0)

    def test_bulk_action_delete_empty(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "delete", "ids": []},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["deleted"], 0)
        self.assertEqual(Cookie.objects.count(), 3)

    def test_bulk_action_delete_nonexistent(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "delete", "ids": [99999]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["deleted"], 0)
        self.assertEqual(Cookie.objects.count(), 3)

    def test_bulk_action_missing_action(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"ids": [self.cookie1.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("action", data)

    def test_bulk_action_missing_ids(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "delete"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("ids", data)

    def test_bulk_action_invalid_ids_type(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "delete", "ids": "not_a_list"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_bulk_action_unsupported_action(self):
        response = self.client.post(
            "/api/cookie/action/",
            {"action": "unsupported", "ids": [self.cookie1.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("not supported", data["error"])

    def test_ids_only_parameter(self):
        response = self.client.get("/api/cookie/?ids_only=1")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        for result in data["results"]:
            self.assertIn("id", result)
            self.assertNotIn("domain", result)
            self.assertNotIn("name", result)
            self.assertNotIn("value", result)

    def test_ids_only_with_search(self):
        response = self.client.get("/api/cookie/?ids_only=1&search=example")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 2)
        for result in data["results"]:
            self.assertIn("id", result)
            self.assertEqual(len(result), 1)

    def test_ids_only_with_pagination(self):
        response = self.client.get("/api/cookie/?ids_only=1&limit=2&offset=0")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(len(data["results"]), 2)
        for result in data["results"]:
            self.assertIn("id", result)
            self.assertEqual(len(result), 1)
