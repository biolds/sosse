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
from datetime import datetime

from django.test import TransactionTestCase
from django.utils.timezone import make_aware

from ..collection import Collection
from ..document import Document
from .test_rest_api import RestAPITest


class CrawlQueueAPITest(RestAPITest, TransactionTestCase):
    def setUp(self):
        super().setUp()
        Document.objects.w_content().delete()
        collection = Collection.create_default()

        Document.objects.create(
            collection=collection,
            url="http://example.com/pending1",
            crawl_last=make_aware(datetime(1998, 1, 1)),
            crawl_next=make_aware(datetime(2003, 1, 1)),
            manual_crawl=False,
        )
        Document.objects.create(
            collection=collection,
            url="http://example.com/pending2",
            crawl_last=make_aware(datetime(1998, 1, 1)),
            crawl_next=make_aware(datetime(2002, 1, 1)),
            manual_crawl=False,
        )
        Document.objects.create(
            collection=collection,
            url="http://example.com/new",
            crawl_last=None,
            crawl_next=make_aware(datetime(2004, 1, 1)),
            manual_crawl=False,
        )

    def test_crawl_queue_status(self):
        response = self.client.get("/api/crawl_queue/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)

        self.assertIn("pause", data)
        self.assertIn("queue", data)
        self.assertIn("queue_new_count", data)
        self.assertIn("queue_recurring_count", data)
        self.assertIn("queue_pending_count", data)
        self.assertIn("now", data)

        self.assertEqual(data["queue_new_count"], 1)
        self.assertEqual(data["queue_recurring_count"], 2)
        self.assertEqual(data["queue_pending_count"], 3)

        self.assertIsInstance(data["queue"], list)
        self.assertEqual(len(data["queue"]), 3)

        for doc in data["queue"]:
            self.assertIn("id", doc)
            self.assertIn("url", doc)
            self.assertIn("crawl_next", doc)
            self.assertIn("crawl_last", doc)
