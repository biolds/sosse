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
from collections import namedtuple
from unittest import mock

from django.test import TransactionTestCase

from .test_rest_api import RestAPITest


class HddStatsTest(RestAPITest, TransactionTestCase):
    @mock.patch("os.statvfs")
    def test_hdd_stats(self, statvfs):
        fakevfs = namedtuple(
            "fakevfs",
            [
                "f_bsize",
                "f_frsize",
                "f_blocks",
                "f_bfree",
                "f_bavail",
                "f_files",
                "f_ffree",
                "f_favail",
                "f_flag",
                "f_namemax",
            ],
        )
        statvfs.side_effect = lambda x: fakevfs(
            f_bsize=4096,
            f_frsize=4096,
            f_blocks=51081736,
            f_bfree=30397904,
            f_bavail=27784887,
            f_files=13049856,
            f_ffree=11610989,
            f_favail=11610989,
            f_flag=4096,
            f_namemax=255,
        )
        response = self.client.get("/api/hdd_stats/")
        self.assertEqual(response.status_code, 200, response.content)

        content = json.loads(response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "db": content["db"],
                "free": 113806897152,
                "html": content["html"],
                "other": content["other"],
                "screenshots": content["screenshots"],
            },
        )
