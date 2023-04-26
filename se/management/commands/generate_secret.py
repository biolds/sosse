# Copyright 2022-2023 Laurent Defert
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

from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = 'Generates a secret key to set in the configuration.'
    doc = 'Generates a secret key that can be used in the :ref:`Configuration file <conf_option_secret_key>`.'

    def handle(self, *args, **options):
        # Escape % to avoid value interpolation in the conf file
        # (https://docs.python.org/3/library/configparser.html#interpolation-of-values)
        print(get_random_secret_key().replace('%', '%%'))
