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

from .test_rest_api import RestAPITest


class MimePluginTest(RestAPITest, TransactionTestCase):
    def test_mime_plugin_list(self):
        response = self.client.get("/api/mime_plugin/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 2)
        self.assertTrue(any(handler["name"] == "Built-in Handler" for handler in data["results"]))
        self.assertTrue(any(handler["name"] == "Custom Handler" for handler in data["results"]))

    def test_mime_plugin_detail(self):
        response = self.client.get(f"/api/mime_plugin/{self.mime_plugin_custom.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "Custom Handler")
        self.assertEqual(data["builtin"], False)

    def test_mime_plugin_create(self):
        response = self.client.post(
            "/api/mime_plugin/",
            {
                "name": "New Handler",
                "description": "A new handler",
                "script": "echo 'new'",
                "mimetype_re": "^image/jpeg$",
                "enabled": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "New Handler")
        self.assertEqual(data["builtin"], False)

    def test_mime_plugin_update_custom(self):
        response = self.client.patch(
            f"/api/mime_plugin/{self.mime_plugin_custom.id}/",
            {"description": "Updated description"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["description"], "Updated description")

    def test_mime_plugin_update_builtin_forbidden(self):
        response = self.client.patch(
            f"/api/mime_plugin/{self.mime_plugin_builtin.id}/",
            {"description": "Should not work"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403, response.content)
        data = json.loads(response.content)
        self.assertIn("for built-in MIME handlers", data["detail"])

    def test_mime_plugin_delete_custom(self):
        response = self.client.delete(f"/api/mime_plugin/{self.mime_plugin_custom.id}/")
        self.assertEqual(response.status_code, 204, response.content)

    def test_mime_plugin_delete_builtin_forbidden(self):
        response = self.client.delete(f"/api/mime_plugin/{self.mime_plugin_builtin.id}/")
        self.assertEqual(response.status_code, 403, response.content)
        data = json.loads(response.content)
        self.assertIn("Cannot delete built-in MIME handlers", data["detail"])

    def test_mime_plugin_builtin_readonly(self):
        response = self.client.post(
            "/api/mime_plugin/",
            {
                "name": "Test Handler",
                "script": "echo 'test'",
                "mimetype_re": "^text/test$",
                "builtin": True,
                "enabled": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["builtin"], False)
