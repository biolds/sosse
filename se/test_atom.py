# Copyright 2024 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

from datetime import timedelta
import feedparser
import tempfile

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from .atom import atom
from .document import Document
from .html_asset import HTMLAsset
from .test_views_mixin import ViewsTestMixin


class AtomTest(ViewsTestMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        Document.objects.create(url='http://127.0.0.1',
                                title='title',
                                content='content',
                                mimetype='text/html',
                                crawl_first=now,
                                crawl_last=now)
        Document.objects.create(url='http://127.0.0.1/bin',
                                title='title',
                                content='content',
                                mimetype='application/octet-stream',
                                crawl_first=yesterday,
                                crawl_last=now)
        HTMLAsset.objects.create(url='http://127.0.0.1/bin',
                                 filename='bin')

    def _atom_get(self, url: str) -> HttpResponse:
        request = self._request_from_factory(url)
        return atom(request)

    def _atom_get_parsed(self, url: str) -> list[dict]:
        response = self._atom_get(url)
        self.assertEqual(response.status_code, 200, response)
        parsed = feedparser.parse(response.content)
        return parsed['entries']

    def test_simple_feed(self):
        entries = self._atom_get_parsed('/atom/?ft1=inc&ff1=doc&fo1=contain&fv1=content')

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['link'], 'http://127.0.0.1')
        self.assertEqual(entries[1]['link'], 'http://127.0.0.1/bin')

    def test_auth(self):
        request = self._request_from_factory('/atom/?ft1=inc&ff1=doc&fo1=contain&fv1=content', AnonymousUser())
        with self.assertRaises(PermissionDenied):
            atom(request)

    @override_settings(SOSSE_ATOM_ACCESS_TOKEN='token42')
    def test_auth_token(self):
        request = self._request_from_factory('/atom/?ft1=inc&ff1=doc&fo1=contain&fv1=content&token=token42', AnonymousUser())
        response = atom(request)
        self.assertEqual(response.status_code, 200)

    def test_cached(self):
        for bin_passthrough in (True, False):
            with tempfile.TemporaryDirectory() as tmp_dir:
                with open(f'{tmp_dir}/bin', 'w') as f:
                    f.write('test')

                with self.settings(SOSSE_HTML_SNAPSHOT_DIR=tmp_dir + '/', SOSSE_ATOM_CACHED_BIN_PASSTHROUGH=bin_passthrough):
                    entries = self._atom_get_parsed('/atom/?ft1=inc&ff1=doc&fo1=contain&fv1=content&cached=1')

            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]['link'], 'http://127.0.0.1/www/http://127.0.0.1')
            if bin_passthrough:
                self.assertEqual(entries[1]['link'], 'http://127.0.0.1/snap/bin')
            else:
                self.assertEqual(entries[1]['link'], 'http://127.0.0.1/download/http://127.0.0.1/bin')
