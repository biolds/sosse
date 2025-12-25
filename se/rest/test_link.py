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

from ..models import Link
from .test_rest_api import RestAPITest


class LinkTest(RestAPITest, TransactionTestCase):
    def setUp(self):
        super().setUp()
        Link.objects.create(
            doc_from=self.doc1,
            doc_to=self.doc2,
            text="Link to doc2",
            pos=0,
            link_no=0,
            screen_pos="100,200",
            in_nav=False,
        )
        Link.objects.create(
            doc_from=self.doc1,
            extern_url="http://external.com",
            text="External link",
            pos=100,
            link_no=1,
            screen_pos="300,400",
            in_nav=True,
        )

    def test_link_by_id(self):
        response = self.client.get(f"/api/link/{self.doc1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)

        self.assertEqual(data[0]["url"], self.doc2.url)
        self.assertEqual(data[0]["title"], self.doc2.title)
        self.assertEqual(data[0]["text"], "Link to doc2")
        self.assertEqual(data[0]["pos"], 0)
        self.assertEqual(data[0]["link_no"], 0)
        self.assertEqual(data[0]["screen_pos"], "100,200")
        self.assertEqual(data[0]["in_nav"], False)
        self.assertEqual(data[0]["available"], True)

        self.assertEqual(data[1]["url"], "http://external.com")
        self.assertEqual(data[1]["title"], "http://external.com")
        self.assertEqual(data[1]["text"], "External link")
        self.assertEqual(data[1]["pos"], 100)
        self.assertEqual(data[1]["link_no"], 1)
        self.assertEqual(data[1]["screen_pos"], "300,400")
        self.assertEqual(data[1]["in_nav"], True)
        self.assertEqual(data[1]["available"], False)

    def test_link_by_url(self):
        response = self.client.get(f"/api/link/{self.doc1.url}")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)

    def test_link_not_found(self):
        response = self.client.get("/api/link/99999/")
        self.assertEqual(response.status_code, 404, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Document not found")

    def test_link_no_links(self):
        response = self.client.get(f"/api/link/{self.doc3.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(len(data), 0)
