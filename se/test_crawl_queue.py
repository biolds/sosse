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

from datetime import datetime

from django.test import TransactionTestCase

from .collection import Collection
from .document import Document


class CrawlQueueTest(TransactionTestCase):
    maxDiff = None

    def setUp(self):
        collection = Collection.create_default()
        Document.objects.create(
            collection=collection,
            url="Pending 1",
            crawl_last=datetime(1998, 1, 1),
            crawl_next=datetime(2003, 1, 1),
            manual_crawl=False,
        )
        Document.objects.create(
            collection=collection,
            url="Pending 2",
            crawl_last=datetime(1998, 1, 1),
            crawl_next=datetime(2002, 1, 1),
            manual_crawl=False,
        )
        Document.objects.create(
            collection=collection,
            url="Pending - first time 1",
            crawl_last=None,
            crawl_next=datetime(2005, 1, 1),
            manual_crawl=False,
        )
        Document.objects.create(
            collection=collection,
            url="Pending - first time 2",
            crawl_last=None,
            crawl_next=datetime(2004, 1, 1),
            manual_crawl=False,
        )

        Document.objects.create(
            collection=collection,
            url="Manual Pending 1",
            crawl_last=datetime(1998, 1, 1),
            crawl_next=datetime(2003, 1, 1),
            manual_crawl=True,
        )
        Document.objects.create(
            collection=collection,
            url="Manual Pending 2",
            crawl_last=datetime(1998, 1, 1),
            crawl_next=datetime(2002, 1, 1),
            manual_crawl=True,
        )
        Document.objects.create(
            collection=collection,
            url="Manual Pending - first time 1",
            crawl_last=None,
            crawl_next=datetime(2005, 1, 1),
            manual_crawl=True,
        )
        Document.objects.create(
            collection=collection,
            url="Manual Pending - first time 2",
            crawl_last=None,
            crawl_next=datetime(2004, 1, 1),
            manual_crawl=True,
        )

        Document.objects.create(
            collection=collection,
            url="In progress 1",
            crawl_last=datetime(2002, 1, 1),
            crawl_next=datetime(2003, 1, 1),
            manual_crawl=False,
            worker_no=1,
        )
        Document.objects.create(
            collection=collection,
            url="In progress 2",
            crawl_last=datetime(2001, 1, 1),
            crawl_next=datetime(2003, 1, 1),
            manual_crawl=False,
            worker_no=2,
        )
        Document.objects.create(
            collection=collection,
            url="In progress 3",
            crawl_last=datetime(1999, 1, 1),
            crawl_next=datetime(2003, 1, 1),
            manual_crawl=False,
            worker_no=3,
        )

        Document.objects.create(
            collection=collection,
            url="Already crawled 1",
            crawl_last=datetime(2001, 1, 1),
            crawl_next=None,
            manual_crawl=False,
        )
        Document.objects.create(
            collection=collection,
            url="Already crawled 2",
            crawl_last=datetime(2000, 1, 1),
            crawl_next=None,
            manual_crawl=False,
        )

    def test_crawl_queue_full_order(self):
        queue = Document.crawl_queue(True)
        queue = [doc.url for doc in queue]
        self.assertEqual(
            list(queue),
            [
                "Pending 1",
                "Pending 2",
                "Pending - first time 1",
                "Pending - first time 2",
                "Manual Pending 1",
                "Manual Pending 2",
                "Manual Pending - first time 1",
                "Manual Pending - first time 2",
                "In progress 1",
                "In progress 2",
                "In progress 3",
                "Already crawled 1",
                "Already crawled 2",
            ],
        )

    def test_crawl_queue_order(self):
        queue = Document.crawl_queue(False).values_list("url", flat=True)
        queue = queue.reverse()
        self.assertEqual(
            list(queue),
            [
                "Pending 1",
                "Pending 2",
                "Pending - first time 1",
                "Pending - first time 2",
                "Manual Pending 1",
                "Manual Pending 2",
                "Manual Pending - first time 1",
                "Manual Pending - first time 2",
            ],
        )
