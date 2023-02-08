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

# Generated by Django 3.2.12 on 2022-12-25 10:18

import datetime
from django.conf import settings
import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models
import django.db.models.deletion
import se.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CrawlerStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('t', models.DateTimeField()),
                ('doc_count', models.PositiveIntegerField()),
                ('queued_url', models.PositiveIntegerField()),
                ('indexing_speed', models.PositiveIntegerField(blank=True, null=True)),
                ('freq', models.CharField(choices=[('M', 'M'), ('D', 'D')], max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='CrawlPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url_regex', models.TextField(unique=True)),
                ('condition', models.CharField(choices=[('always', 'Crawl all pages'), ('depth', 'Depending on depth'), ('never', 'Never crawl')], default='always', max_length=6)),
                ('mimetype_regex', models.TextField(default='text/.*')),
                ('crawl_depth', models.PositiveIntegerField(default=0, help_text="Level of external links (links that don't match the regex) to recurse into")),
                ('keep_params', models.BooleanField(default=True, help_text='When disabled, URL parameters (parameters after "?") are removed from URLs, this can be useful if some parameters are random, change sorting or filtering, ...', verbose_name='Index URL parameters')),
                ('default_browse_mode', models.CharField(choices=[('detect', 'Detect'), ('selenium', 'Chromium'), ('requests', 'Python Requests')], default='detect', help_text="Python Request is faster, but can't execute Javascript and may break pages", max_length=8)),
                ('take_screenshots', models.BooleanField(default=False)),
                ('screenshot_format', models.CharField(choices=[('png', 'png'), ('jpg', 'jpg')], default='jpg', max_length=3)),
                ('script', models.TextField(blank=True, default='', help_text='Javascript code to execute after the page is loaded')),
                ('store_extern_links', models.BooleanField(default=False)),
                ('recrawl_mode', models.CharField(choices=[('none', 'Once'), ('constant', 'Constant time'), ('adaptive', 'Adaptive')], default='adaptive', help_text='Adaptive frequency will increase delay between two crawls when the page stays unchanged', max_length=8, verbose_name='Crawl frequency')),
                ('recrawl_dt_min', models.DurationField(blank=True, default=datetime.timedelta(days=1), help_text='Min. time before recrawling a page', null=True)),
                ('recrawl_dt_max', models.DurationField(blank=True, default=datetime.timedelta(days=365), help_text='Max. time before recrawling a page', null=True)),
                ('hash_mode', models.CharField(choices=[('raw', 'Hash raw content'), ('no_numbers', 'Normalize numbers before')], default='no_numbers', help_text='Page content hashing method used to detect changes in the content', max_length=10)),
                ('auth_login_url_re', models.TextField(blank=True, help_text='A redirection to this URL will trigger authentication', null=True, verbose_name='Login URL')),
                ('auth_form_selector', models.TextField(blank=True, help_text='CSS selector pointing to the authentication &lt;form&gt; element', null=True, verbose_name='Form selector')),
            ],
            options={
                'verbose_name_plural': 'crawl policies',
            },
        ),
        migrations.CreateModel(
            name='DomainSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('browse_mode', models.CharField(choices=[('detect', 'Detect'), ('selenium', 'Chromium'), ('requests', 'Python Requests')], default='detect', max_length=10)),
                ('domain', models.TextField(unique=True)),
                ('robots_status', models.CharField(choices=[('unknown', 'Unknown'), ('empty', 'Empty'), ('loaded', 'Loaded'), ('ignore', 'Ignore')], default='unknown', max_length=10, verbose_name='robots.txt status')),
                ('robots_ua_hash', models.CharField(blank=True, default='', max_length=32)),
                ('robots_allow', models.TextField(blank=True, default='', verbose_name='robots.txt allow rules')),
                ('robots_disallow', models.TextField(blank=True, default='', verbose_name='robots.txt disallow rules')),
                ('ignore_robots', models.BooleanField(default=False, verbose_name='Ignore robots.txt')),
            ],
        ),
        migrations.CreateModel(
            name='ExcludedUrl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.TextField(unique=True)),
                ('comment', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='FavIcon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.TextField(unique=True)),
                ('content', models.BinaryField(blank=True, null=True)),
                ('mimetype', models.CharField(blank=True, max_length=64, null=True)),
                ('missing', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='SearchEngine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_name', models.CharField(blank=True, default='', max_length=32)),
                ('long_name', models.CharField(blank=True, default='', max_length=48)),
                ('description', models.CharField(blank=True, default='', max_length=1024)),
                ('html_template', models.CharField(max_length=2048, validators=[se.models.validate_search_url])),
                ('shortcut', models.CharField(blank=True, max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='WorkerStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doc_processed', models.PositiveIntegerField(default=0)),
                ('worker_no', models.IntegerField()),
                ('pid', models.PositiveIntegerField()),
                ('state', models.CharField(choices=[('idle', 'Idle'), ('running', 'Running'), ('paused', 'Paused')], default='idle', max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name='SearchHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.TextField()),
                ('querystring', models.TextField()),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.TextField(unique=True)),
                ('normalized_url', models.TextField()),
                ('title', models.TextField()),
                ('normalized_title', models.TextField()),
                ('content', models.TextField()),
                ('normalized_content', models.TextField()),
                ('content_hash', models.TextField(blank=True, null=True)),
                ('vector', django.contrib.postgres.search.SearchVectorField(blank=True, null=True)),
                ('lang_iso_639_1', models.CharField(blank=True, max_length=6, null=True, verbose_name='Language')),
                ('vector_lang', se.models.RegConfigField(default='simple')),
                ('mimetype', models.CharField(blank=True, max_length=64, null=True)),
                ('robotstxt_rejected', models.BooleanField(default=False, verbose_name='Rejected by robots.txt')),
                ('redirect_url', models.TextField(blank=True, null=True)),
                ('screenshot_file', models.CharField(blank=True, max_length=4096, null=True)),
                ('screenshot_count', models.PositiveIntegerField(blank=True, null=True)),
                ('screenshot_size', models.CharField(max_length=16)),
                ('screenshot_format', models.CharField(choices=[('png', 'png'), ('jpg', 'jpg')], max_length=3)),
                ('crawl_first', models.DateTimeField(blank=True, null=True, verbose_name='Crawled first')),
                ('crawl_last', models.DateTimeField(blank=True, null=True, verbose_name='Crawled last')),
                ('crawl_next', models.DateTimeField(blank=True, null=True, verbose_name='Crawl next')),
                ('crawl_dt', models.DurationField(blank=True, null=True, verbose_name='Crawl DT')),
                ('crawl_recurse', models.PositiveIntegerField(default=0, verbose_name='Recursion remaining')),
                ('error', models.TextField(blank=True, default='')),
                ('error_hash', models.TextField(blank=True, default='')),
                ('worker_no', models.PositiveIntegerField(blank=True, null=True)),
                ('favicon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='se.favicon')),
            ],
        ),
        migrations.CreateModel(
            name='Cookie',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.TextField(help_text='Domain name')),
                ('domain_cc', models.TextField(help_text='Domain name attribute from the cookie')),
                ('inc_subdomain', models.BooleanField()),
                ('name', models.TextField(blank=True)),
                ('value', models.TextField(blank=True)),
                ('path', models.TextField(default='/')),
                ('expires', models.DateTimeField(blank=True, null=True)),
                ('secure', models.BooleanField()),
                ('same_site', models.CharField(choices=[('Lax', 'Lax'), ('Strict', 'Strict'), ('None', 'None')], default='Strict', max_length=6)),
                ('http_only', models.BooleanField(default=False)),
            ],
            options={
                'unique_together': {('domain_cc', 'name', 'path')},
            },
        ),
        migrations.CreateModel(
            name='AuthField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=256, verbose_name='<input> name attribute')),
                ('value', models.CharField(max_length=256)),
                ('crawl_policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='se.crawlpolicy')),
            ],
            options={
                'verbose_name': 'authentication field',
            },
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True, null=True)),
                ('pos', models.PositiveIntegerField()),
                ('link_no', models.PositiveIntegerField()),
                ('extern_url', models.TextField(blank=True, null=True)),
                ('screen_pos', models.CharField(blank=True, max_length=64, null=True)),
                ('doc_from', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='links_to', to='se.document')),
                ('doc_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linked_from', to='se.document')),
            ],
            options={
                'unique_together': {('doc_from', 'link_no')},
            },
        ),
        migrations.AddIndex(
            model_name='document',
            index=django.contrib.postgres.indexes.GinIndex(fields=['vector'], name='se_document_vector_efded7_gin'),
        ),
    ]
