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

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand


class UpdateBuiltinModel(BaseCommand):
    json_file = None
    model_class = None
    lookup_field = None
    model_name = None
    fields_to_remove = set()

    def handle(self, *args, **options):
        count = 0

        json_file_path = os.path.join(settings.BASE_DIR, self.json_file)
        for item in json.load(open(json_file_path, encoding="utf-8")):
            fields = item.copy()
            for field in self.fields_to_remove:
                fields.pop(field, None)

            lookup_value = fields.pop(self.lookup_field)

            db_obj, created = self.model_class.objects.get_or_create(
                **{self.lookup_field: lookup_value}, defaults=fields
            )

            if not created:
                self.update_existing(db_obj, fields)

            count += int(created)

        self.stdout.write(f"{count} new {self.model_name} added")
        self.check_conflicts()

    def update_existing(self, db_obj, fields):
        if not db_obj.builtin:
            self.stderr.write(
                self.style.WARNING(
                    f"Skipping update of {self.model_name.rstrip('s')} '{getattr(db_obj, self.lookup_field)}' "
                    f"because it is user-defined"
                )
            )
            return
        # Remove 'enabled' field to preserve user's enable/disable choice
        fields.pop("enabled", None)
        # Use save() instead of update() to ensure overridden save method is called
        # (e.g., MimePlugin needs to write the JSON configuration file to disk)
        for field, value in fields.items():
            setattr(db_obj, field, value)
        db_obj.save()

    def check_conflicts(self):
        pass
