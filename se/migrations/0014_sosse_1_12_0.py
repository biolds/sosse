# Copyright 2025 Laurent Defert
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

# Generated by Django 3.2.19 on 2025-01-08 13:09
import os

from django.db import migrations, models

from sosse.conf import CONF_FILE

OPTS_UPDATE = (
    ("atom_cached_bin_passthrough", "atom_archive_bin_passthrough"),
    ("cache_follows_redirect", "archive_follows_redirects"),
)


def update_cache_conf(apps, schema_editor):
    try:
        if os.path.exists(CONF_FILE):
            with open(CONF_FILE) as f:
                content = f.read()

            new_content = content

            for old_val, new_val in OPTS_UPDATE:
                new_content = new_content.replace(old_val, new_val)

            if new_content != content:
                with open(CONF_FILE, "w") as f:
                    f.write(new_content)
    except Exception:  # nosec B110
        pass


def reverse_cache_conf(apps, schema_editor):
    try:
        if os.path.exists(CONF_FILE):
            with open(CONF_FILE) as f:
                content = f.read()

            new_content = content

            for old_val, new_val in OPTS_UPDATE:
                new_content = new_content.replace(new_val, old_val)

            if new_content != content:
                with open(CONF_FILE, "w") as f:
                    f.write(new_content)
    except Exception:  # nosec B110
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0013_sosse_1_11_0"),
    ]

    operations = [
        migrations.RunPython(update_cache_conf, reverse_cache_conf),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="mimetype_regex",
            field=models.TextField(default=".*"),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="auth_login_url_re",
            field=models.TextField(
                blank=True,
                help_text="A redirection to an URL matching the regex will trigger authentication",
                null=True,
                verbose_name="Login URL regex",
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="snapshot_exclude_element_re",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Regex of HTML elements to skip related assets downloading",
                verbose_name="Assets exclude HTML regex",
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="snapshot_exclude_mime_re",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Regex of mimetypes to skip related assets saving",
                verbose_name="Assets exclude mime regex",
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="snapshot_exclude_url_re",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Regex of URL to skip related assets downloading",
                verbose_name="Assets exclude URL regex",
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="snapshot_html",
            field=models.BooleanField(
                default=True,
                help_text="Archive binary files, HTML content and download related assets",
                verbose_name="Archive content 🔖",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="modified_date",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Last modification date"),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="thumbnail_mode",
            field=models.CharField(
                choices=[
                    ("preview", "Page preview from metadata"),
                    ("prevscreen", "Preview from meta, screenshot as fallback"),
                    ("screenshot", "Take a screenshot"),
                    ("none", "No thumbnail"),
                ],
                default="preview",
                help_text="Save thumbnails to display in search results",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="default_browse_mode",
            field=models.CharField(
                choices=[
                    ("detect", "Detect"),
                    ("selenium", "Chromium"),
                    ("firefox", "Firefox"),
                    ("requests", "Python Requests"),
                ],
                default="detect",
                help_text="Python Request is faster, but can't execute Javascript and may break pages",
                max_length=8,
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="thumbnail_mode",
            field=models.CharField(
                choices=[
                    ("preview", "Page preview from metadata"),
                    ("prevscreen", "Preview from meta, screenshot as fallback"),
                    ("screenshot", "Take a screenshot"),
                    ("none", "No thumbnail"),
                ],
                default="preview",
                help_text="Save thumbnails to display in search results",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="default_browse_mode",
            field=models.CharField(
                choices=[
                    ("detect", "Detect"),
                    ("selenium", "Chromium"),
                    ("firefox", "Firefox"),
                    ("requests", "Python Requests"),
                ],
                default="detect",
                help_text="Python Request is faster, but can't execute Javascript and may break pages",
                max_length=8,
            ),
        ),
    ]
