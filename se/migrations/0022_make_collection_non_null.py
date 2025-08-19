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

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0021_populate_document_collection"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collection",
            name="name",
            field=models.CharField(max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name="document",
            name="collection",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="se.collection"),
        ),
        migrations.RemoveField(
            model_name="collection",
            name="recursion",
        ),
        migrations.RemoveField(
            model_name="collection",
            name="enabled",
        ),
    ]
