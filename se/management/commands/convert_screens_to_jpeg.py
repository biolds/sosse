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

from django.core.management.base import BaseCommand

from ...document import Document


class Command(BaseCommand):
    help = "Convert all PNG screenshots to JPEG format."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually converting",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write("DRY RUN: Showing what would be converted...")
        else:
            self.stdout.write("Converting PNG screenshots to JPEG...")

        documents_to_convert = (
            Document.objects.wo_content().exclude(screenshot_format=Document.SCREENSHOT_JPG).exclude(screenshot_count=0)
        )

        total_count = documents_to_convert.count()
        self.stdout.write(f"Found {total_count} documents with PNG screenshots to convert.")

        if total_count == 0:
            self.stdout.write("No documents need conversion.")
            return

        converted_count = 0

        for doc in documents_to_convert:
            if dry_run:
                self.stdout.write(f"Would convert: {doc.url}")
            else:
                try:
                    self.stdout.write(f"Converting: {doc.url}")
                    doc.convert_to_jpg()
                    doc.screenshot_format = Document.SCREENSHOT_JPG
                    doc.save()
                    converted_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error converting {doc.url}: {e}"))

        if dry_run:
            self.stdout.write(f"DRY RUN: Would convert {total_count} documents.")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully converted {converted_count} out of {total_count} documents.")
            )
