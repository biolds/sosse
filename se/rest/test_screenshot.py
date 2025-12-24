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


class ScreenshotTest(RestAPITest, TransactionTestCase):
    def test_screenshot_with_links(self):
        self.doc1.screenshot_count = 1
        self.doc1.screenshot_format = "png"
        self.doc1.screenshot_size = "1024x768"
        self.doc1.save()

        Link.objects.create(
            doc_from=self.doc1, doc_to=self.doc2, text="Link text", pos=100, link_no=1, screen_pos="10,20,30,40"
        )

        response = self.client.get(f"/api/screenshot/{self.doc1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)

        self.assertIn("screenshot", data)
        self.assertIn("links", data)
        self.assertEqual(len(data["links"]), 1)
        self.assertEqual(data["links"][0]["text"], "Link text")
        self.assertEqual(data["links"][0]["screen_pos"], "10,20,30,40")

    def test_screenshot_not_found(self):
        response = self.client.get("/api/screenshot/99999/")
        self.assertEqual(response.status_code, 404, response.content)

    def test_screenshot_no_screenshot_available(self):
        response = self.client.get(f"/api/screenshot/{self.doc1.id}/")
        self.assertEqual(response.status_code, 404, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["error"], "No screenshot available")

    def test_screenshot_by_url(self):
        self.doc1.screenshot_count = 1
        self.doc1.screenshot_format = "jpg"
        self.doc1.save()

        response = self.client.get(f"/api/screenshot/{self.doc1.url}")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertIn("screenshot", data)
