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

from unittest import mock

from django.test import TransactionTestCase

from .collection import Collection
from .document import Document
from .domain import Domain
from .html_asset import HTMLAsset
from .models import WorkerStats
from .test_mock import BrowserMock


class DocumentTest(TransactionTestCase):
    def setUp(self):
        self.collection = Collection.objects.create(
            name="Test Collection",
            unlimited_regex="(default)",
            unlimited_regex_pg=".*",
            default_browse_mode=Domain.BROWSE_REQUESTS,
            thumbnail_mode=Collection.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )

    def _crawl(self, url="http://127.0.0.1/"):
        # Force create the worker
        WorkerStats.get_worker(0)

        Document.queue(url, self.collection, None)
        while Document.crawl(0):
            pass

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_010_html_delete(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({})

        self._crawl("http://127.0.0.1/page.html")

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(HTMLAsset.objects.count(), 1)

        doc = Document.objects.wo_content().get()
        self.assertTrue(doc.has_html_snapshot)
        Document.objects.wo_content().first().delete_all()

        self.assertEqual(HTMLAsset.objects.count(), 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_020_image_html_delete(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({})

        self._crawl("http://127.0.0.1/image.png")

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(HTMLAsset.objects.count(), 1)

        doc = Document.objects.wo_content().get()
        self.assertTrue(doc.has_html_snapshot)
        Document.objects.wo_content().first().delete_all()

        self.assertEqual(HTMLAsset.objects.count(), 0)
