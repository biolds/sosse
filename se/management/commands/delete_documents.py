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

import sys
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...document import Document
from ...utils import human_datetime


class Command(BaseCommand):
    help = "Mass delete documents."

    def add_arguments(self, parser):
        parser.add_argument("url regex")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Prints the count of documents that would be deleted.",
        )
        parser.add_argument(
            "-i",
            "--ignore-case",
            action="store_true",
            help="Case insensitive matching.",
        )
        parser.add_argument(
            "--exclude",
            help="Regex pattern to exclude URLs from deletion.",
        )

    def handle(self, *args, **options):
        if options["ignore_case"]:
            docs = Document.objects.wo_content().filter(url__iregex=options["url regex"])
        else:
            docs = Document.objects.wo_content().filter(url__regex=options["url regex"])

        if options["exclude"]:
            if options["ignore_case"]:
                docs = docs.exclude(url__iregex=options["exclude"])
            else:
                docs = docs.exclude(url__regex=options["exclude"])

        count = docs.count()
        if options["dry_run"]:
            self.stdout.write(f"{count} documents would be deleted")
            sys.exit(0)

        self.stdout.write(f"Deleting {docs.count()} documents, please wait...")

        start_time = progress_time = timezone.now()
        for no, doc in enumerate(docs):
            doc.delete_all()
            doc.delete()

            if progress_time + timedelta(minutes=1) < timezone.now():
                progress = (no / count) * 100
                progress_time = timezone.now()
                doc_dt = (progress_time - start_time) / (no + 1)
                eta = (count - (no + 1)) * doc_dt
                self.stdout.write(f"{progress:.1f}%\t ETA ~{human_datetime(eta, True)}")

        self.stdout.write("Done")
