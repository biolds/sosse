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

from django.db import connection, reset_queries
from django.test import TransactionTestCase

from .crawl_policy import CrawlPolicy
from .document import Document
from .domain_setting import DomainSetting
from .page import Page
from .test_mock import BrowserMock


class DocumentIndexTest(TransactionTestCase):
    def setUp(self):
        self.crawl_policy = CrawlPolicy.objects.create(
            url_regex="(default)",
            url_regex_pg=".*",
            recursion=CrawlPolicy.CRAWL_NEVER,
            default_browse_mode=DomainSetting.BROWSE_REQUESTS,
            thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )

    def assertQueriesCountEqual(self, count):
        sql_queries = [q["sql"] for q in connection.queries if q["sql"].startswith('SELECT "se_document"."id"')]
        self.assertEqual(len(sql_queries), count, "\n".join(sql_queries))

    def test_010_defer_queue_pick(self):
        reset_queries()
        Document.queue("http://127.0.0.1/", None, None)
        self.assertQueriesCountEqual(1)

        reset_queries()
        Document.pick_queued(0)
        self.assertQueriesCountEqual(2)

    def test_020_defer_index(self):
        page = Page("http://127.0.0.1", b"", None)
        doc = Document.objects.wo_content().create(url="http://127.0.0.1")

        reset_queries()
        doc.index(page, self.crawl_policy)
        self.assertQueriesCountEqual(0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_030_defer_crawl(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        Document.queue("http://127.0.0.1/", None, None)

        reset_queries()
        Document.crawl(0)

        self.assertEqual(Document.objects.count(), 1)
