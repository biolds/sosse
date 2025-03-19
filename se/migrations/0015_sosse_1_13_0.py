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

# Generated by Django 3.2.19 on 2025-02-12 10:06

import mptt.fields
from django.db import migrations, models

import se


class Migration(migrations.Migration):
    dependencies = [
        ("se", "0014_sosse_1_12_0"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crawlpolicy",
            name="hash_mode",
            field=models.CharField(
                choices=[("raw", "Raw content"), ("no_numbers", "Normalize numbers")],
                default="no_numbers",
                help_text="Content to check for modifications",
                max_length=10,
                verbose_name="Change detection",
            ),
        ),
        migrations.RenameField(
            model_name="crawlpolicy",
            old_name="recrawl_mode",
            new_name="recrawl_freq",
        ),
        migrations.AddField(
            model_name="crawlpolicy",
            name="recrawl_condition",
            field=models.CharField(
                choices=[("change", "On change only"), ("always", "Always"), ("manual", "On change or manual trigger")],
                default="manual",
                help_text="Specifies the conditions under which a page is reprocessed",
                max_length=10,
                verbose_name="Condition",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="manual_crawl",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="searchengine",
            name="builtin",
            field=models.BooleanField(default=False, verbose_name="Built-in"),
        ),
        migrations.AddField(
            model_name="searchengine",
            name="enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("lft", models.PositiveIntegerField(editable=False)),
                ("rght", models.PositiveIntegerField(editable=False)),
                ("tree_id", models.PositiveIntegerField(db_index=True, editable=False)),
                ("level", models.PositiveIntegerField(editable=False)),
                (
                    "parent",
                    mptt.fields.TreeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.CASCADE,
                        related_name="children",
                        to="se.tag",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="document",
            name="tags",
            field=models.ManyToManyField(blank=True, to="se.Tag"),
        ),
        migrations.AddField(
            model_name="crawlpolicy",
            name="tags",
            field=models.ManyToManyField(blank=True, to="se.Tag"),
        ),
        migrations.CreateModel(
            name="Webhook",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=512, unique=True)),
                (
                    "trigger_condition",
                    models.CharField(
                        choices=[
                            ("change", "On content change"),
                            ("discovery", "On discovery"),
                            ("always", "On every crawl"),
                            ("manual", "On content change or manual crawl"),
                        ],
                        default="manual",
                        max_length=10,
                    ),
                ),
                ("url", models.URLField()),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("get", "GET"),
                            ("post", "POST"),
                            ("put", "PUT"),
                            ("patch", "PATCH"),
                            ("delete", "DELETE"),
                        ],
                        default="post",
                        max_length=10,
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        blank=True,
                        help_text="Username for basic authentication, leave empty for no auth",
                        max_length=128,
                    ),
                ),
                (
                    "password",
                    models.CharField(
                        blank=True,
                        help_text="Password for basic authentication, leave empty for no auth",
                        max_length=128,
                    ),
                ),
                (
                    "headers",
                    models.TextField(
                        blank=True,
                        help_text="Additional headers to send with the request",
                        validators=[se.webhook.parse_headers],
                    ),
                ),
                (
                    "body_template",
                    models.TextField(
                        default=dict,
                        help_text="Template for the request body",
                        validators=[se.webhook.validate_template],
                        verbose_name="JSON body template",
                    ),
                ),
                (
                    "mimetype_re",
                    models.CharField(
                        blank=True,
                        default=".*",
                        help_text="Run the webhook on pages with mimetype matching this regex",
                        max_length=128,
                        validators=[se.utils.validate_multiline_re],
                        verbose_name="Mimetype regex",
                    ),
                ),
                (
                    "title_re",
                    models.TextField(
                        blank=True,
                        default=".*",
                        help_text="Run the webhook on pages with title matching these regexs. (one by line, lines starting with # are ignored)",
                        validators=[se.utils.validate_multiline_re],
                        verbose_name="Title regex",
                    ),
                ),
                (
                    "content_re",
                    models.TextField(
                        blank=True,
                        default=".*",
                        help_text="Run the webhook on pages with content matching this regexs. (one by line, lines starting with # are ignored)",
                        validators=[se.utils.validate_multiline_re],
                        verbose_name="Content regex",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="document",
            name="webhooks_result",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="crawlpolicy",
            name="webhooks",
            field=models.ManyToManyField(to="se.Webhook"),
        ),
        migrations.AlterModelOptions(
            name="cookie",
            options={},
        ),
        migrations.AlterModelOptions(
            name="crawlpolicy",
            options={"verbose_name": "Crawl Policy", "verbose_name_plural": "Crawl Policies"},
        ),
        migrations.AlterModelOptions(
            name="document",
            options={},
        ),
        migrations.AlterModelOptions(
            name="domainsetting",
            options={},
        ),
        migrations.AlterModelOptions(
            name="excludedurl",
            options={"verbose_name": "Excluded URL", "verbose_name_plural": "Excluded URLs"},
        ),
        migrations.AlterModelOptions(
            name="searchengine",
            options={"verbose_name": "Search Engine", "verbose_name_plural": "Search Engines"},
        ),
        migrations.AlterModelOptions(
            name="webhook",
            options={},
        ),
    ]
