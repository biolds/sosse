# Copyright 2022-2025 Laurent Defert
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

from django.conf import settings

from ...admin import ConflictingSearchEngineFilter
from ...models import SearchEngine
from ..builtin import UpdateBuiltinModel


class Command(UpdateBuiltinModel):
    help = "Updates Search engine shortcuts."
    doc = "This updates :doc:`user/shortcuts` in the database based on their definition in the source code."

    json_file = "sosse/search_engines.json"
    model_class = SearchEngine
    lookup_field = "short_name"
    model_name = "search engines"

    def update_existing(self, db_obj, fields):
        fields.pop("shortcut")
        return super().update_existing(db_obj, fields)

    def check_conflicts(self):
        conflicts = ConflictingSearchEngineFilter.conflicts(SearchEngine.objects.all())

        if len(conflicts):
            conflicts = conflicts.values_list("shortcut", flat=True).order_by("shortcut")
            sc = ", ".join([settings.SOSSE_SEARCH_SHORTCUT_CHAR + c for c in conflicts])
            self.stderr.write(self.style.ERROR(f"WARNING: {len(conflicts)} shortcuts are in conflict: {sc}"))
            exit(1)
