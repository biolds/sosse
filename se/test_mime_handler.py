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

import os

from django.test import TransactionTestCase, override_settings

from .collection import Collection
from .document import Document
from .mime_handler import MimeHandler
from .page import Page

TEST_CONTENT = "dumy data"


class MimeHandlerTests(TransactionTestCase):
    def setUp(self):
        self.collection = Collection.create_default()
        self.doc = Document.objects.create(mimetype="application/pdf", collection=self.collection, content="", error="")
        self.page = Page("http://127.0.0.1", TEST_CONTENT.encode("utf-8"), None)

    def test_json_doc_handler_execution(self):
        handler = MimeHandler.objects.create(
            name="PDF JSON Extractor",
            script='echo \'{"title": "My PDF"}\'',
            mimetype_re="^application/pdf$",
            enabled=True,
        )

        MimeHandler.run_for_document(self.doc, self.page)

        self.assertEqual(self.doc.content, "")
        self.assertEqual(self.doc.error, "")
        self.assertEqual(self.doc.title, "My PDF")
        self.assertTrue(os.path.exists(handler.get_script_path()))

    def test_handler_with_error_output(self):
        MimeHandler.objects.create(
            name="Failing Handler",
            script="exit 1",
            mimetype_re="^application/pdf$",
            enabled=True,
        )

        MimeHandler.run_for_document(self.doc, self.page)

        self.assertIn("Failing Handler", self.doc.error)
        self.assertEqual(self.doc.content, "")

    @override_settings(TEST_MODE=False)
    def test_handler_processing_error_json_invalid(self):
        MimeHandler.objects.create(
            name="Invalid JSON Handler",
            script="echo 'not a json'",
            mimetype_re="^application/pdf$",
            enabled=True,
        )

        MimeHandler.run_for_document(self.doc, self.page)

        self.assertIn("output is not valid JSON", self.doc.error)
        self.assertEqual(self.doc.content, "")

    def test_non_matching_mimetype(self):
        MimeHandler.objects.create(
            name="Other Type Handler",
            script="echo 'should not run'",
            mimetype_re="^image/.*$",
            enabled=True,
        )

        MimeHandler.run_for_document(self.doc, self.page)

        self.assertEqual(self.doc.content, "")
        self.assertEqual(self.doc.error, "")

    def test_enabled_field_prevents_execution(self):
        MimeHandler.objects.create(
            name="Disabled Handler",
            script="echo 'Should not run'",
            mimetype_re="^application/pdf$",
            enabled=False,
        )

        MimeHandler.run_for_document(self.doc, self.page)

        self.assertEqual(self.doc.content, "")
        self.assertEqual(self.doc.error, "")

    def test_mimetype_re_supports_multiple_patterns(self):
        MimeHandler.objects.create(
            name="Multiple Mimetypes Handler",
            script='echo \'{"content": "multi content"}\'',
            mimetype_re="^text/plain$\n^application/pdf$",
            enabled=True,
        )
        MimeHandler.run_for_document(self.doc, self.page)
        self.assertEqual(self.doc.content, "multi content")
        self.assertEqual(self.doc.error, "")

    def test_json_output(self):
        MimeHandler.objects.create(
            name="JSON Output Handler",
            script='echo \'{"title": "Output Format JSON"}\'',
            mimetype_re="^application/pdf$",
            enabled=True,
        )
        MimeHandler.run_for_document(self.doc, self.page)
        self.assertEqual(self.doc.title, "Output Format JSON")
        self.assertEqual(self.doc.error, "")

    def test_handler_timeout(self):
        MimeHandler.objects.create(
            name="Timeout Handler",
            script="sleep 5; echo fail",
            mimetype_re="^application/pdf$",
            timeout=1,
            enabled=True,
        )
        MimeHandler.run_for_document(self.doc, self.page)

        self.assertIn("Timeout", self.doc.error)
        self.assertEqual(self.doc.content, "")

    def test_handler_command_not_found(self):
        MimeHandler.objects.create(
            name="Missing Command",
            script="non_existent_command_xyz",
            mimetype_re="^application/pdf$",
            enabled=True,
        )
        MimeHandler.run_for_document(self.doc, self.page)
        self.assertIn("not found", self.doc.error)
        self.assertEqual(self.doc.content, "")

    def test_json_handler_with_input_file(self):
        MimeHandler.objects.create(
            name="Modify JSON Input",
            script=r"""#!/bin/bash
FILE="$1"
TITLE=$(jq -r '.title' "$FILE")
CONTENT=$(jq -r '.content' "$FILE")
URL=$(jq -r '.url' "$FILE")
echo "{\"title\": \"Modified $TITLE\", \"content\": \"Modified $CONTENT\"}"
""",
            mimetype_re="^application/pdf$",
            enabled=True,
        )
        self.doc.title = "Original Title"
        self.doc.content = "Original Content"
        self.doc.save()

        MimeHandler.run_for_document(self.doc, self.page)
        self.assertEqual(self.doc.title, "Modified Original Title")
        self.assertEqual(self.doc.content, "Modified Original Content")

    def test_json_handler_url_readonly(self):
        MimeHandler.objects.create(
            name="Modify JSON Input",
            script=r"""#!/bin/bash
FILE="$1"
TITLE=$(jq -r '.title' "$FILE")
CONTENT=$(jq -r '.content' "$FILE")
URL=$(jq -r '.url' "$FILE")
echo "{\"title\": \"Modified $TITLE\", \"content\": \"Modified $CONTENT\", \"url\": \"${URL}/modified\"}"
""",
            mimetype_re="^application/pdf$",
            enabled=True,
        )
        self.doc.title = "Original Title"
        self.doc.content = "Original Content"
        self.doc.url = "https://original/"
        self.doc.save()

        MimeHandler.run_for_document(self.doc, self.page)
        self.assertEqual(self.doc.title, "Modified Original Title")
        self.assertEqual(self.doc.content, "Modified Original Content")
        self.assertEqual(self.doc.url, "https://original/")

    def test_json_handler_normalized_fields(self):
        MimeHandler.objects.create(
            name="Modify JSON Input",
            script=r"""#!/bin/bash
FILE="$1"
TITLE=$(jq -r '.title' "$FILE")
CONTENT=$(jq -r '.content' "$FILE")
echo "{\"title\": \"Modifièd $TITLE\", \"content\": \"Modifiéd $CONTENT\"}"
""",
            mimetype_re="^application/pdf$",
            enabled=True,
        )
        self.doc.title = "Original Title"
        self.doc.content = "Original Content"
        self.doc.save()

        MimeHandler.run_for_document(self.doc, self.page)
        self.assertEqual(self.doc.title, "Modifièd Original Title")
        self.assertEqual(self.doc.normalized_title, "Modified Original Title")
        self.assertEqual(self.doc.content, "Modifiéd Original Content")
        self.assertEqual(self.doc.normalized_content, "Modified Original Content")
