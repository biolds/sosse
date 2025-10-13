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

import csv
import io
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from .csv import CsvView
from .document import Document
from .test_views_mixin import ViewsTestMixin


class CsvTest(ViewsTestMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.doc = Document.objects.wo_content().create(
            url="http://127.0.0.1",
            title="title",
            content="content",
            mimetype="text/html",
            crawl_first=timezone.now() - timedelta(days=1),
            crawl_last=timezone.now(),
            collection=self.collection,
        )

    def _csv_to_dict(self, csv_data):
        """Convert CSV data to a list of dictionaries."""
        headers = csv_data[0]
        _csv_data = []
        for row in csv_data[1:]:
            _csv_data.append(dict(zip(headers, row)))
        return _csv_data

    def _check_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")

        csv_reader = csv.reader(io.StringIO(content))
        csv_data = list(csv_reader)
        csv_data = self._csv_to_dict(csv_data)

        self.assertEqual(len(csv_data), 1)
        self.assertEqual(csv_data[0]["url"], self.doc.url)
        self.assertEqual(csv_data[0]["title"], self.doc.title)

    def test_simple_feed(self):
        request = self._request_from_factory("/csv/?ft1=inc&ff1=doc&fo1=contain&fv1=content", self.admin_user)
        response = CsvView.as_view()(request)
        self._check_response(response)

    def test_flat_metadata(self):
        self.doc.metadata = {"key1": "value1", "key2": "value2"}
        self.doc.save()
        request = self._request_from_factory("/csv/?ft1=inc&ff1=doc&fo1=contain&fv1=content", self.admin_user)
        response = CsvView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")

        csv_reader = csv.reader(io.StringIO(content))
        csv_data = list(csv_reader)
        csv_data = self._csv_to_dict(csv_data)

        self.assertEqual(len(csv_data), 1)
        self.assertEqual(csv_data[0]["metadata key1"], "value1")
        self.assertEqual(csv_data[0]["metadata key2"], "value2")

    def test_heterogeneous_metadata(self):
        self.doc.metadata = {"key1": "value1", "key2": "value2"}
        self.doc.save()
        Document.objects.wo_content().create(
            url="http://127.0.0.1/other",
            title="title",
            content="content new",
            mimetype="text/html",
            crawl_first=timezone.now() - timedelta(days=1),
            crawl_last=timezone.now(),
            metadata={"key1": "value3", "key3": "plop"},
            collection=self.collection,
        )

        request = self._request_from_factory("/csv/?ft1=inc&ff1=doc&fo1=contain&fv1=content", self.admin_user)
        response = CsvView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")

        csv_reader = csv.reader(io.StringIO(content))
        csv_data = list(csv_reader)
        csv_data = self._csv_to_dict(csv_data)

        self.assertEqual(len(csv_data), 2)
        self.assertEqual(csv_data[0]["metadata key1"], "value3")
        self.assertEqual(csv_data[0]["metadata key2"], "")
        self.assertEqual(csv_data[0]["metadata key3"], "plop")
        self.assertEqual(csv_data[1]["metadata key1"], "value1")
        self.assertEqual(csv_data[1]["metadata key2"], "value2")
        self.assertEqual(csv_data[1]["metadata key3"], "")

    @override_settings(SOSSE_CSV_EXPORT=False)
    def test_csv_disabled(self):
        request = self._request_from_factory("/csv/?ft1=inc&ff1=doc&fo1=contain&fv1=content", self.admin_user)
        self.assertRaises(
            PermissionDenied,
            CsvView.as_view(),
            request,
        )

    def test_anonymous_export(self):
        request = self._request_from_factory("/csv/?ft1=inc&ff1=doc&fo1=contain&fv1=content", self.anon_user)
        self.assertRaises(
            PermissionDenied,
            CsvView.as_view(),
            request,
        )

    @override_settings(SOSSE_ANONYMOUS_SEARCH=True)
    def test_anonymous_export_authorized(self):
        request = self._request_from_factory("/csv/?ft1=inc&ff1=doc&fo1=contain&fv1=content", self.anon_user)
        self._check_response(CsvView.as_view()(request))
