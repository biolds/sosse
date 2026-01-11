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

from ..domain import Domain
from .test_rest_api import RestAPITest


class DomainRestTest(RestAPITest, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.domain1 = Domain.objects.create(
            domain="example.com",
            browse_mode=Domain.BROWSE_DETECT,
            robots_status=Domain.ROBOTS_UNKNOWN,
            ignore_robots=False,
        )
        self.domain2 = Domain.objects.create(
            domain="test.org",
            browse_mode=Domain.BROWSE_CHROMIUM,
            robots_status=Domain.ROBOTS_LOADED,
            robots_allow="/api/*",
            robots_disallow="/admin/*",
            robots_ua_hash="abc123",
            ignore_robots=False,
        )
        self.domain3 = Domain.objects.create(
            domain="norestrictions.net",
            browse_mode=Domain.BROWSE_FIREFOX,
            robots_status=Domain.ROBOTS_EMPTY,
            ignore_robots=True,
        )

    def test_domain_list(self):
        response = self.client.get("/api/domain/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

    def test_domain_detail(self):
        response = self.client.get(f"/api/domain/{self.domain1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["id"], self.domain1.id)
        self.assertEqual(data["domain"], "example.com")
        self.assertEqual(data["browse_mode"], Domain.BROWSE_DETECT)
        self.assertEqual(data["robots_status"], Domain.ROBOTS_UNKNOWN)
        self.assertFalse(data["ignore_robots"])

    def test_domain_create(self):
        response = self.client.post(
            "/api/domain/",
            {
                "domain": "newdomain.com",
                "browse_mode": Domain.BROWSE_REQUESTS,
                "robots_status": Domain.ROBOTS_UNKNOWN,
                "ignore_robots": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["domain"], "newdomain.com")
        self.assertEqual(data["browse_mode"], Domain.BROWSE_REQUESTS)
        self.assertFalse(data["ignore_robots"])

    def test_domain_update(self):
        response = self.client.patch(
            f"/api/domain/{self.domain1.id}/",
            {"browse_mode": Domain.BROWSE_FIREFOX, "ignore_robots": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["browse_mode"], Domain.BROWSE_FIREFOX)
        self.assertTrue(data["ignore_robots"])

    def test_domain_delete(self):
        response = self.client.delete(f"/api/domain/{self.domain3.id}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(Domain.objects.filter(id=self.domain3.id).exists())

    def test_domain_search(self):
        response = self.client.get("/api/domain/?search=example")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "example.com")

    def test_domain_filter_by_browse_mode(self):
        response = self.client.get(f"/api/domain/?browse_mode={Domain.BROWSE_CHROMIUM}")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "test.org")

    def test_domain_filter_by_robots_status(self):
        response = self.client.get(f"/api/domain/?robots_status={Domain.ROBOTS_LOADED}")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "test.org")

    def test_domain_filter_by_ignore_robots(self):
        response = self.client.get("/api/domain/?ignore_robots=true")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["domain"], "norestrictions.net")

    def test_domain_ordering(self):
        response = self.client.get("/api/domain/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        domains = [result["domain"] for result in data["results"]]
        self.assertEqual(domains, ["example.com", "norestrictions.net", "test.org"])

    def test_domain_ordering_desc(self):
        response = self.client.get("/api/domain/?ordering=-domain")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        domains = [result["domain"] for result in data["results"]]
        self.assertEqual(domains, ["test.org", "norestrictions.net", "example.com"])

    def test_domain_pagination(self):
        response = self.client.get("/api/domain/?limit=2")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 2)
