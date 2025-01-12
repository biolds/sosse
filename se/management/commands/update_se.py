# Copyright 2022-2025 Laurent Defert
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

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from ...admin import ConflictingSearchEngineFilter
from ...models import SearchEngine

SE_FILE = "sosse/search_engines.json"


class Command(BaseCommand):
    help = "Updates Search engine shortcuts."
    doc = "This updates :doc:`user/shortcuts` in the database based on their definition in the source code."

    def handle(self, *args, **options):
        count = 0

        se_file = os.path.join(settings.BASE_DIR, SE_FILE)
        for se in json.load(open(se_file)):
            if se["model"] != "se.searchengine":
                raise ValueError(f"Invalid model {se['model']} in {se_file}")
            se = se["fields"]
            short_name = se.pop("short_name")

            db_se, created = SearchEngine.objects.get_or_create(short_name=short_name, defaults=se)

            if not created:
                se.pop("shortcut")
                SearchEngine.objects.filter(id=db_se.id).update(**se)

            count += int(created)

        self.stdout.write(f"{count} new search engines added")
        conflicts = ConflictingSearchEngineFilter.conflicts(SearchEngine.objects.all())

        if len(conflicts):
            conflicts = conflicts.values_list("shortcut", flat=True).order_by("shortcut")
            sc = ", ".join([settings.SOSSE_SEARCH_SHORTCUT_CHAR + c for c in conflicts])
            self.stderr.write(self.style.ERROR(f"WARNING: {len(conflicts)} shortcuts are in conflict: {sc}"))
            exit(1)
