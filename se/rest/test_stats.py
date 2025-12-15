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

from .test_rest_api import RestAPITest, now_str

SERIALIZED_CRAWLER_STATS = [
    {"doc_count": 23, "freq": "M", "indexing_speed": 2, "queued_url": 24, "t": now_str},
    {"doc_count": 33, "freq": "D", "indexing_speed": 4, "queued_url": 34, "t": now_str},
]


class StatsTest(RestAPITest, TransactionTestCase):
    def test_stats_list(self):
        response = self.client.get("/api/stats/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_CRAWLER_STATS[0] | {"id": self.crawler_stat1.id},
                    SERIALIZED_CRAWLER_STATS[1] | {"id": self.crawler_stat2.id},
                ],
            },
        )

    def test_stats_detail(self):
        response = self.client.get(f"/api/stats/{self.crawler_stat1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            SERIALIZED_CRAWLER_STATS[0] | {"id": self.crawler_stat1.id},
        )

    def test_stats_list_filter(self):
        response = self.client.get("/api/stats/?freq=M")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_CRAWLER_STATS[0] | {"id": self.crawler_stat1.id},
                ],
            },
        )

    def test_lang_stats(self):
        response = self.client.get("/api/lang_stats/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), [{"doc_count": 3, "lang": "En 🇬🇧"}])

    def test_mime_stats(self):
        response = self.client.get("/api/mime_stats/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            [{"mimetype": "🌐 text/html", "doc_count": 2}, {"mimetype": "🖼️ image/png", "doc_count": 1}],
            response.content,
        )
