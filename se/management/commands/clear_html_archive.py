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

from django.core.management.base import BaseCommand

from ...html_asset import HTMLAsset


class Command(BaseCommand):
    help = "Clears archived HTML snapshots."

    def handle(self, *args, **options):
        self.stdout.write("Clearing archive, please wait...")
        HTMLAsset.objects.update(download_date=None)
        self.stdout.write("Done.")
