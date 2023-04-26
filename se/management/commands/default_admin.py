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

import sys

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates a default ``admin`` superuser with ``admin`` password,\ndoes nothing if at least one user already exists in the database.'

    def handle(self, *args, **options):
        if User.objects.count() != 0:
            self.stdout.write('The database already has a user, skipping default user creation')
            sys.exit(0)

        user = User.objects.create(username='admin', is_superuser=True, is_staff=True, is_active=True)
        user.set_password('admin')
        user.save()
        self.stdout.write('Default user "admin", with password "admin" was created')
