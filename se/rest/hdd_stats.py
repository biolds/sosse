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

from django.conf import settings
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from .permissions import IsSuperUserOrStaff


class HddStatsSerializer(serializers.Serializer):
    db = serializers.IntegerField(help_text="Size of the database")
    screenshots = serializers.IntegerField(help_text="Size of the screenshots")
    html = serializers.IntegerField(help_text="Size of HTML dumps")
    other = serializers.IntegerField(help_text="Data not used by Sosse")
    free = serializers.IntegerField(help_text="Free space")


class HddStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    def dir_size(self, d):
        # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
        size = 0
        for dirpath, _, filenames in os.walk(d):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    size += os.path.getsize(fp)
        return size

    @extend_schema(
        description="HDD analytics",
        responses={
            200: HddStatsSerializer(),
        },
    )
    def list(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_database_size(%s)", [settings.DATABASES["default"]["NAME"]])
            db_size = cursor.fetchall()[0][0]

        statvfs = os.statvfs("/var/lib")
        hdd_size = statvfs.f_frsize * statvfs.f_blocks
        hdd_free = statvfs.f_frsize * statvfs.f_bavail

        screenshot_size = self.dir_size(settings.SOSSE_SCREENSHOTS_DIR)
        html_size = self.dir_size(settings.SOSSE_HTML_SNAPSHOT_DIR)
        hdd_other = hdd_size - hdd_free - db_size - screenshot_size - html_size
        return Response(
            {
                "db": db_size,
                "screenshots": screenshot_size,
                "html": html_size,
                "other": hdd_other,
                "free": hdd_free,
            }
        )
