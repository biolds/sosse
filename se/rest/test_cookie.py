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

from ..cookie import Cookie
from .test_rest_api import RestAPITest


class CookieRestTest(RestAPITest, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.cookie1 = Cookie.objects.create(
            domain="example.com",
            name="session_id",
            value="abc123",
            path="/",
            inc_subdomain=False,
            secure=False,
            same_site=Cookie.SAME_SITE_LAX,
        )
        self.cookie2 = Cookie.objects.create(
            domain="test.com",
            domain_cc=".test.com",
            name="auth_token",
            value="xyz789",
            path="/api",
            inc_subdomain=True,
            secure=True,
            same_site=Cookie.SAME_SITE_STRICT,
            http_only=True,
            expires=timezone.now() + timezone.timedelta(days=30),
        )
        self.cookie3 = Cookie.objects.create(
            domain="example.org",
            name="tracking",
            value="tracking123",
            path="/",
            inc_subdomain=False,
            secure=False,
        )

    def test_cookie_list(self):
        response = self.client.get("/api/cookie/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

    def test_cookie_detail(self):
        response = self.client.get(f"/api/cookie/{self.cookie1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["id"], self.cookie1.id)
        self.assertEqual(data["domain"], "example.com")
        self.assertEqual(data["name"], "session_id")
        self.assertEqual(data["value"], "abc123")
        self.assertEqual(data["path"], "/")
        self.assertFalse(data["inc_subdomain"])
        self.assertFalse(data["secure"])
        self.assertEqual(data["same_site"], Cookie.SAME_SITE_LAX)

    def test_cookie_create(self):
        response = self.client.post(
            "/api/cookie/",
            {
                "domain": "newsite.com",
                "name": "new_cookie",
                "value": "new_value",
                "path": "/test",
                "inc_subdomain": False,
                "secure": True,
                "same_site": Cookie.SAME_SITE_NONE,
                "http_only": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["domain"], "newsite.com")
        self.assertEqual(data["name"], "new_cookie")
        self.assertEqual(data["value"], "new_value")
        self.assertTrue(data["secure"])

    def test_cookie_update(self):
        response = self.client.patch(
            f"/api/cookie/{self.cookie1.id}/",
            {"value": "updated_value", "secure": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["value"], "updated_value")
        self.assertTrue(data["secure"])

    def test_cookie_delete(self):
        response = self.client.delete(f"/api/cookie/{self.cookie3.id}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(Cookie.objects.filter(id=self.cookie3.id).exists())

    def test_cookie_search_by_domain(self):
        response = self.client.get("/api/cookie/?search=example")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 2)
        domains = [result["domain"] for result in data["results"]]
        self.assertIn("example.com", domains)
        self.assertIn("example.org", domains)

    def test_cookie_search_by_path(self):
        response = self.client.get("/api/cookie/?search=/api")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "test.com")

    def test_cookie_search_by_url(self):
        response = self.client.get("/api/cookie/?search=http://example.com/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "example.com")
        self.assertEqual(data["results"][0]["name"], "session_id")

    def test_cookie_search_by_https_url(self):
        response = self.client.get("/api/cookie/?search=https://test.com/api/endpoint")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "test.com")
        self.assertEqual(data["results"][0]["name"], "auth_token")

    def test_cookie_search_subdomain_url(self):
        response = self.client.get("/api/cookie/?search=https://sub.test.com/api/test")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        if data["count"] > 0:
            self.assertEqual(data["results"][0]["domain"], "test.com")

    def test_cookie_ordering(self):
        response = self.client.get("/api/cookie/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        domains = [result["domain"] for result in data["results"]]
        self.assertEqual(sorted(domains), ["example.com", "example.org", "test.com"])
