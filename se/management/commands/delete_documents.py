# Copyright 2022-2024 Laurent Defert
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

import sys
from datetime import timedelta

from django.utils import timezone
from django.core.management.base import BaseCommand

from ...document import Document
from ...utils import human_datetime


class Command(BaseCommand):
    help = 'Mass delete documents.'

    def add_arguments(self, parser):
        parser.add_argument('url regexp')
        parser.add_argument('--dry-run', action='store_true', help="Prints the count of documents that would be deleted.")
        parser.add_argument('-i', '--ignore-case', action='store_true', help='Case insensitive matching.')

    def handle(self, *args, **options):
        if options['ignore_case']:
            docs = Document.objects.filter(url__regex=options['url regexp'])
        else:
            docs = Document.objects.filter(url__iregex=options['url regexp'])

        count = docs.count()
        if options['dry_run']:
            self.stdout.write('%s documents would be deleted' % count)
            sys.exit(0)

        self.stdout.write('Deleting %s documents, please wait...' % docs.count())

        start_time = progress_time = timezone.now()
        for no, doc in enumerate(docs):
            doc.delete_all()
            doc.delete()

            if progress_time + timedelta(minutes=1) < timezone.now():
                progress = (no / count) * 100
                progress_time = timezone.now()
                doc_dt = (progress_time - start_time) / (no + 1)
                eta = ((count - (no + 1)) * doc_dt)
                self.stdout.write('%0.1f%%\t ETA ~%s' % (progress, human_datetime(eta, True)))

        self.stdout.write('Done')
