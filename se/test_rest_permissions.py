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

from django.contrib.auth.models import Permission, User
from django.test import TransactionTestCase, override_settings

from .collection import Collection
from .document import Document
from .test_rest_api import RestAPITest


class RestAPIAuthTest(RestAPITest, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.client.logout()
        self.regular_user = User.objects.create_user(username="user", password="user")

    @override_settings(SOSSE_ANONYMOUS_SEARCH=True)
    def test_search_anonymous(self):
        response = self.client.post("/api/search/", {"query": "content"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content).get("count"), 1)

        # Document API requires authentication and view_document permission
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 403, response.content)

    @override_settings(SOSSE_ANONYMOUS_SEARCH=False)
    def test_search_anonymous_forbidden(self):
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 403, response.content)

        response = self.client.post("/api/search/", {"query": "content"})
        self.assertEqual(response.status_code, 403, response.content)

        self.client.login(username="admin", password="admin")
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content).get("count"), 3)

        response = self.client.post("/api/search/", {"query": "content"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content).get("count"), 1)

    @override_settings(SOSSE_ANONYMOUS_SEARCH=True)
    def test_crawler_stats_permission(self):
        response = self.client.get("/api/stats/")
        self.assertEqual(response.status_code, 403, response.content)

        self.client.login(username="user", password="user")
        response = self.client.get("/api/stats/")
        self.assertEqual(response.status_code, 403, response.content)

        self.client.logout()
        self.client.login(username="admin", password="admin")
        response = self.client.get("/api/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content).get("count"), 2)

    @override_settings(SOSSE_ANONYMOUS_SEARCH=True)
    def test_hdd_stats_permission(self):
        response = self.client.get("/api/hdd_stats/")
        self.assertEqual(response.status_code, 403, response.content)

        self.client.login(username="user", password="user")
        response = self.client.get("/api/hdd_stats/")
        self.assertEqual(response.status_code, 403, response.content)

        self.client.logout()
        self.client.login(username="admin", password="admin")
        response = self.client.get("/api/hdd_stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(json.loads(response.content).keys()),
            {"db", "screenshots", "html", "other", "free"},
        )

    def test_document_update_permission(self):
        collection = Collection.create_default()
        doc = Document.objects.create(
            url="http://example.com", collection=collection, title="Example", content="Example content"
        )
        response = self.client.patch(
            f"/api/document/{doc.id}/", {"title": "New title"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403, response.content)

        self.client.login(username="user", password="user")
        response = self.client.patch(
            f"/api/document/{doc.id}/", {"title": "New title"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403, response.content)

        permission = Permission.objects.get(codename="change_document")
        self.regular_user.user_permissions.add(permission)
        self.assertTrue(self.regular_user.has_perm("se.change_document"))
        self.client.logout()
        self.client.login(username="user", password="user")
        response = self.client.patch(
            f"/api/document/{doc.id}/", {"title": "New title"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content).get("title"), "New title")
