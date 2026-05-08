# Copyright 2026 Laurent Defert
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

from django.db import migrations, models


def create_browser_configs(apps, schema_editor):
    BrowserConfig = apps.get_model("se", "BrowserConfig")
    for browser in ("requests", "chromium", "firefox"):
        BrowserConfig.objects.get_or_create(browser=browser)


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0025_alter_collection_queue_to_any_collection_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BrowserConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "browser",
                    models.CharField(
                        choices=[
                            ("requests", "Python Requests"),
                            ("chromium", "Chromium"),
                            ("firefox", "Firefox"),
                        ],
                        max_length=10,
                        unique=True,
                    ),
                ),
                (
                    "ignore_ssl_errors",
                    models.BooleanField(
                        default=False,
                        help_text="Disable SSL certificate validation for this browser. This allows crawling pages with expired or otherwise invalid certificates.",
                        verbose_name="Ignore SSL certificate errors",
                    ),
                ),
                (
                    "extra_options",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Additional command-line options appended to Chromium or Firefox. Ignored by Python Requests.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Browser configuration",
                "verbose_name_plural": "Browser configurations",
            },
        ),
        migrations.RunPython(create_browser_configs, migrations.RunPython.noop),
    ]
