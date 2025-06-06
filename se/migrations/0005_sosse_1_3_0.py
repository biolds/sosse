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

# Generated by Django 3.2.19 on 2023-07-24 09:16

from django.db import migrations, models


def forward_default_snapshot(apps, schema_editor):
    CrawlPolicy = apps.get_model("se", "CrawlPolicy")
    CrawlPolicy.objects.update(snapshot_html=False)


def reverse_default_snapshot(apps, schema_editor):
    pass


def forward_update_external_links(apps, schema_editor):
    Document = apps.get_model("se", "Document")
    Link = apps.get_model("se", "Link")
    for link in Link.objects.filter(extern_url__isnull=False):
        doc = Document.objects.filter(url=link.extern_url).first()
        if doc:
            link.extern_url = None
            link.doc_to = doc
            link.save()


def reverse_update_external_links(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0004_sosse_1_2_0"),
    ]

    operations = [
        migrations.AddField(
            model_name="crawlpolicy",
            name="snapshot_html",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="crawlpolicy",
            name="take_screenshots",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="document",
            name="has_html_snapshot",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forward_default_snapshot, reverse_default_snapshot),
        migrations.AddField(
            model_name="crawlpolicy",
            name="snapshot_exclude_element_re",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Regexp of elements to skip asset downloading",
            ),
        ),
        migrations.AddField(
            model_name="crawlpolicy",
            name="snapshot_exclude_mime_re",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Regexp of mimetypes to skip asset saving",
            ),
        ),
        migrations.AddField(
            model_name="crawlpolicy",
            name="snapshot_exclude_url_re",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Regexp of URL to skip asset downloading",
            ),
        ),
        migrations.CreateModel(
            name="HTMLAsset",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("url", models.TextField()),
                ("filename", models.TextField()),
                ("ref_count", models.PositiveBigIntegerField(default=0)),
                ("download_date", models.DateTimeField(blank=True, null=True)),
                ("last_modified", models.DateTimeField(blank=True, null=True)),
                ("max_age", models.PositiveBigIntegerField(blank=True, null=True)),
                ("has_cache_control", models.BooleanField(default=False)),
                ("etag", models.CharField(max_length=128, null=True, blank=True)),
            ],
            options={
                "unique_together": {("url", "filename")},
            },
        ),
        migrations.RunPython(forward_update_external_links, reverse_update_external_links),
    ]
