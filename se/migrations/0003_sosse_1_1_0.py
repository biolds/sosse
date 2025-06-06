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

# Generated by Django 3.2.12 on 2023-05-29 08:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0002_search_vector"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="show_on_homepage",
            field=models.BooleanField(default=False, help_text="Display this document on the homepage"),
        ),
    ]
