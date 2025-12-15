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

from django.contrib.auth.models import User
from django.utils import timezone

from ..collection import Collection
from ..document import Document
from ..mime_plugin import MimePlugin
from ..models import CrawlerStats
from ..tag import Tag
from ..test_client import Client
from ..webhook import Webhook

now = timezone.now()
now_str = now.isoformat().replace("+00:00", "Z")
SERIALIZED_DOC1_BASE = {
    "content_hash": None,
    "crawl_dt": None,
    "crawl_first": now_str,
    "crawl_last": now_str,
    "crawl_next": None,
    "crawl_recurse": 0,
    "error": "",
    "error_hash": "",
    "favicon": None,
    "has_html_snapshot": False,
    "has_thumbnail": False,
    "hidden": False,
    "lang_iso_639_1": "en",
    "manual_crawl": False,
    "metadata": {},
    "mime_plugins_result": "",
    "mimetype": "text/html",
    "modified_date": None,
    "normalized_title": "title",
    "normalized_url": "http test",
    "preview": None,
    "redirect_url": None,
    "retries": 0,
    "robotstxt_rejected": False,
    "screenshot_count": 0,
    "screenshot_format": "",
    "screenshot_size": "",
    "show_on_homepage": False,
    "snapshot_url": None,
    "tags": [],
    "tags_str": "",
    "title": "Title",
    "too_many_redirects": False,
    "url": "http://127.0.0.1/test",
    "vector_lang": "simple",
    "webhooks_result": {},
    "worker_no": None,
}
SERIALIZED_DOC1 = SERIALIZED_DOC1_BASE | {
    "content": "Content",
    "normalized_content": "content",
    "vector": "'content':4C 'http':2A 'test':3A 'title':1A",
}
SERIALIZED_DOC2_BASE = SERIALIZED_DOC1_BASE | {
    "url": "http://127.0.0.1/test2",
    "normalized_url": "http test2",
    "title": "Title2",
    "normalized_title": "title2",
    "mimetype": "image/png",
    "tags": ["Sub Tag"],
    "tags_str": "Sub Tag",
}
SERIALIZED_DOC3_BASE = SERIALIZED_DOC1_BASE | {
    "url": "http://example.com/test3",
    "normalized_url": "http example com test3",
    "title": "Title3",
    "normalized_title": "title3",
}


class RestAPITest:
    maxDiff = None

    def setUp(self):
        self.collection = Collection.create_default()
        self.collection2 = Collection.objects.create(name="Test Collection 2", unlimited_regex="http://example.com/.*")
        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.user = User.objects.create_user(username="admin", password="admin", is_superuser=True)
        self.user.save()

        self.client.login(username="admin", password="admin")

        self.doc1 = Document.objects.wo_content().create(
            url="http://127.0.0.1/test",
            normalized_url="http test",
            title="Title",
            normalized_title="title",
            content="Content",
            normalized_content="content",
            crawl_first=now,
            crawl_last=now,
            lang_iso_639_1="en",
            mimetype="text/html",
            collection=self.collection,
        )
        self.doc2 = Document.objects.wo_content().create(
            url="http://127.0.0.1/test2",
            normalized_url="http test2",
            title="Title2",
            normalized_title="title2",
            content="Other Content2",
            normalized_content="other content2",
            crawl_first=now,
            crawl_last=now,
            lang_iso_639_1="en",
            mimetype="image/png",
            collection=self.collection,
        )
        self.doc3 = Document.objects.wo_content().create(
            url="http://example.com/test3",
            normalized_url="http example com test3",
            title="Title3",
            normalized_title="title3",
            content="Content3",
            normalized_content="content3",
            crawl_first=now,
            crawl_last=now,
            lang_iso_639_1="en",
            mimetype="text/html",
            collection=self.collection2,
        )

        self.crawler_stat1 = CrawlerStats.objects.create(t=now, doc_count=23, queued_url=24, indexing_speed=2, freq="M")
        self.crawler_stat2 = CrawlerStats.objects.create(t=now, doc_count=33, queued_url=34, indexing_speed=4, freq="D")

        self.tag = Tag.objects.create(name="Group")
        self.subtag = Tag.objects.create(name="Sub Tag", parent=self.tag)
        self.doc2.tags.set([self.subtag])

        self.test_webhook = Webhook.objects.create(name="Test Webhook", url="http://test.com/webhook")

        self.mime_plugin_builtin = MimePlugin.objects.create(
            name="Built-in Handler",
            description="A built-in MIME handler",
            script="echo 'builtin'",
            mimetype_re="^text/plain$",
            builtin=True,
            enabled=True,
        )
        self.mime_plugin_custom = MimePlugin.objects.create(
            name="Custom Handler",
            description="A custom MIME handler",
            script="echo 'custom'",
            mimetype_re="^application/json$",
            builtin=False,
            enabled=True,
        )
