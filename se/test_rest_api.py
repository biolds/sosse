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

import json
from collections import namedtuple
from unittest import mock

from django.contrib.auth.models import User
from django.test import Client, TransactionTestCase
from django.utils import timezone

from .collection import Collection
from .document import Document
from .mime_plugin import MimePlugin
from .models import CrawlerStats
from .tag import Tag
from .webhook import Webhook

now = timezone.now()
now_str = now.isoformat().replace("+00:00", "Z")
SERIALIZED_DOC1 = {
    "content": "Content",
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
    "normalized_content": "content",
    "normalized_title": "title",
    "normalized_url": "http test",
    "redirect_url": None,
    "retries": 0,
    "robotstxt_rejected": False,
    "screenshot_count": 0,
    "screenshot_format": "",
    "screenshot_size": "",
    "show_on_homepage": False,
    "tags": [],
    "tags_str": "",
    "title": "Title",
    "too_many_redirects": False,
    "url": "http://127.0.0.1/test",
    "vector": "'content':4C 'http':2A 'test':3A 'title':1A",
    "vector_lang": "simple",
    "webhooks_result": {},
    "worker_no": None,
}
SERIALIZED_DOC2 = SERIALIZED_DOC1 | {
    "url": "http://127.0.0.1/test2",
    "normalized_url": "http test2",
    "title": "Title2",
    "normalized_title": "title2",
    "content": "Other Content2",
    "normalized_content": "other content2",
    "mimetype": "image/png",
    "tags": ["Sub Tag"],
    "tags_str": "Sub Tag",
    "vector": "'content2':5C 'http':2A 'other':4C 'test2':3A 'title2':1A",
}
SERIALIZED_DOC3 = SERIALIZED_DOC1 | {
    "url": "http://example.com/test3",
    "normalized_url": "http example com test3",
    "title": "Title3",
    "normalized_title": "title3",
    "content": "Content3",
    "normalized_content": "content3",
    "vector": "'com':4A 'content3':6C 'example':3A 'http':2A 'test3':5A 'title3':1A",
}


SERIALIZED_CRAWLER_STATS = [
    {"doc_count": 23, "freq": "M", "indexing_speed": 2, "queued_url": 24, "t": now_str},
    {"doc_count": 33, "freq": "D", "indexing_speed": 4, "queued_url": 34, "t": now_str},
]


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


class APIQueryTest(RestAPITest, TransactionTestCase):
    def test_document_list(self):
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["next"], None)
        self.assertEqual(data["previous"], None)

        doc_ids = [result["id"] for result in data["results"]]
        self.assertIn(self.doc1.id, doc_ids)
        self.assertIn(self.doc2.id, doc_ids)
        self.assertIn(self.doc3.id, doc_ids)

    def test_document_detail(self):
        response = self.client.get(f"/api/document/{self.doc1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content), SERIALIZED_DOC1 | {"id": self.doc1.id, "collection": self.collection.id}
        )

    def test_stats_list(self):
        response = self.client.get("/api/stats/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_CRAWLER_STATS[0] | {"id": self.crawler_stat1.id},
                    SERIALIZED_CRAWLER_STATS[1] | {"id": self.crawler_stat2.id},
                ],
            },
        )

    def test_stats_detail(self):
        response = self.client.get(f"/api/stats/{self.crawler_stat1.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            SERIALIZED_CRAWLER_STATS[0] | {"id": self.crawler_stat1.id},
        )

    def test_stats_list_filter(self):
        response = self.client.get("/api/stats/?freq=M")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_CRAWLER_STATS[0] | {"id": self.crawler_stat1.id},
                ],
            },
        )

    @mock.patch("os.statvfs")
    def test_hdd_stats(self, statvfs):
        fakevfs = namedtuple(
            "fakevfs",
            [
                "f_bsize",
                "f_frsize",
                "f_blocks",
                "f_bfree",
                "f_bavail",
                "f_files",
                "f_ffree",
                "f_favail",
                "f_flag",
                "f_namemax",
            ],
        )
        statvfs.side_effect = lambda x: fakevfs(
            f_bsize=4096,
            f_frsize=4096,
            f_blocks=51081736,
            f_bfree=30397904,
            f_bavail=27784887,
            f_files=13049856,
            f_ffree=11610989,
            f_favail=11610989,
            f_flag=4096,
            f_namemax=255,
        )
        response = self.client.get("/api/hdd_stats/")
        self.assertEqual(response.status_code, 200, response.content)

        content = json.loads(response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "db": content["db"],
                "free": 113806897152,
                "html": content["html"],
                "other": content["other"],
                "screenshots": content["screenshots"],
            },
        )

    def test_lang_stats(self):
        response = self.client.get("/api/lang_stats/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), [{"doc_count": 3, "lang": "En 🇬🇧"}])

    def test_mime_stats(self):
        response = self.client.get("/api/mime_stats/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            [{"mimetype": "🌐 text/html", "doc_count": 2}, {"mimetype": "🖼️ image/png", "doc_count": 1}],
            response.content,
        )

    def test_search(self):
        response = self.client.post("/api/search/", {"query": "content"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC1
                    | {
                        "collection": self.collection.id,
                        "id": self.doc1.id,
                        "score": 0.12158542,
                    }
                ],
            },
        )

    def test_search_has_params(self):
        response = self.client.post("/api/search/", {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content),
            {"non_field_errors": ['At least "query" or "adv_params" field must be provided.']},
        )

    def test_search_title(self):
        response = self.client.post(
            "/api/search/",
            {"adv_params": [{"field": "content", "term": "Content2"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC2
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 1.0,
                    }
                ],
            },
        )

    def test_search_hidden(self):
        self.doc2.hidden = True
        self.doc2.save()

        response = self.client.post("/api/search/", {"query": "http"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC1
                    | {
                        "collection": self.collection.id,
                        "id": self.doc1.id,
                        "score": 0.6079271,
                    },
                    SERIALIZED_DOC3
                    | {
                        "collection": self.collection2.id,
                        "id": self.doc3.id,
                        "score": 0.6079271,
                    },
                ],
            },
        )

    def test_search_hidden_included(self):
        self.doc2.hidden = True
        self.doc2.save()

        response = self.client.post("/api/search/", {"query": "http", "include_hidden": True})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC1
                    | {
                        "collection": self.collection.id,
                        "id": self.doc1.id,
                        "score": 0.6079271,
                    },
                    SERIALIZED_DOC2
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 0.6079271,
                        "hidden": True,
                    },
                    SERIALIZED_DOC3
                    | {
                        "collection": self.collection2.id,
                        "id": self.doc3.id,
                        "score": 0.6079271,
                    },
                ],
            },
        )

    def test_search_tags(self):
        response = self.client.post(
            "/api/search/",
            {"adv_params": [{"field": "tag", "term": "Sub Tag", "operator": "equal"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC2
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 1.0,
                    },
                ],
            },
        )

    def test_search_subtags(self):
        response = self.client.post(
            "/api/search/",
            {"adv_params": [{"field": "tag", "term": "Group", "operator": "equal"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            json.loads(response.content),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    SERIALIZED_DOC2
                    | {
                        "collection": self.collection.id,
                        "id": self.doc2.id,
                        "score": 1.0,
                    },
                ],
            },
        )

    def test_document_tags_str_update(self):
        response = self.client.patch(
            f"/api/document/{self.doc1.id}/", {"tags": ["tag1", "tag2"]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.doc1.refresh_from_db()
        tags = list(self.doc1.tags.values_list("name", flat=True))
        self.assertEqual(tags, ["tag1", "tag2"])

    def test_document_tags_pk_update(self):
        tag = Tag.objects.create(name="test tag")
        response = self.client.patch(
            f"/api/document/{self.doc1.id}/", {"tags": [tag.pk]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.doc1.refresh_from_db()
        tags = list(self.doc1.tags.values_list("name", flat=True))
        self.assertEqual(tags, ["test tag"])

    def test_document_normalize(self):
        response = self.client.patch(
            f"/api/document/{self.doc1.id}/", {"title": "tïtle", "content": "contènt"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.normalized_title, "title")
        self.assertEqual(self.doc1.normalized_content, "content")

    def test_document_create_prohibited(self):
        response = self.client.post("/api/document/", {"url": "http://127.0.0.1/"}, content_type="application/json")
        self.assertEqual(response.status_code, 405, response.content)

    def test_mime_plugin_list(self):
        response = self.client.get("/api/mime_plugin/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 2)
        self.assertTrue(any(handler["name"] == "Built-in Handler" for handler in data["results"]))
        self.assertTrue(any(handler["name"] == "Custom Handler" for handler in data["results"]))

    def test_mime_plugin_detail(self):
        response = self.client.get(f"/api/mime_plugin/{self.mime_plugin_custom.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "Custom Handler")
        self.assertEqual(data["builtin"], False)

    def test_mime_plugin_create(self):
        response = self.client.post(
            "/api/mime_plugin/",
            {
                "name": "New Handler",
                "description": "A new handler",
                "script": "echo 'new'",
                "mimetype_re": "^image/jpeg$",
                "enabled": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "New Handler")
        self.assertEqual(data["builtin"], False)

    def test_mime_plugin_update_custom(self):
        response = self.client.patch(
            f"/api/mime_plugin/{self.mime_plugin_custom.id}/",
            {"description": "Updated description"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["description"], "Updated description")

    def test_mime_plugin_update_builtin_forbidden(self):
        response = self.client.patch(
            f"/api/mime_plugin/{self.mime_plugin_builtin.id}/",
            {"description": "Should not work"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403, response.content)
        data = json.loads(response.content)
        self.assertIn("for built-in MIME handlers", data["detail"])

    def test_mime_plugin_delete_custom(self):
        response = self.client.delete(f"/api/mime_plugin/{self.mime_plugin_custom.id}/")
        self.assertEqual(response.status_code, 204, response.content)

    def test_mime_plugin_delete_builtin_forbidden(self):
        response = self.client.delete(f"/api/mime_plugin/{self.mime_plugin_builtin.id}/")
        self.assertEqual(response.status_code, 403, response.content)
        data = json.loads(response.content)
        self.assertIn("Cannot delete built-in MIME handlers", data["detail"])

    def test_mime_plugin_builtin_readonly(self):
        response = self.client.post(
            "/api/mime_plugin/",
            {
                "name": "Test Handler",
                "script": "echo 'test'",
                "mimetype_re": "^text/test$",
                "builtin": True,
                "enabled": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["builtin"], False)

    def test_search_collection_filter(self):
        response = self.client.post("/api/search/", {"query": "content", "collection": self.collection.id})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.doc1.id)

    def test_search_collection_filter_different(self):
        response = self.client.post("/api/search/", {"query": "content3", "collection": self.collection2.id})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.doc3.id)

    def test_search_no_collection_filter(self):
        response = self.client.post("/api/search/", {"query": "http"})
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 3)
        doc_ids = [result["id"] for result in data["results"]]
        self.assertIn(self.doc1.id, doc_ids)
        self.assertIn(self.doc2.id, doc_ids)
        self.assertIn(self.doc3.id, doc_ids)

    def test_search_collection_nonexistent(self):
        response = self.client.post("/api/search/", {"query": "content", "collection": 99999})
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("Collection with id 99999 does not exist", data["collection"][0])

    def test_collection_list(self):
        response = self.client.get("/api/collection/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["count"], 2)

        collection_names = [result["name"] for result in data["results"]]
        self.assertEqual(len(collection_names), 2)
        self.assertIn(self.collection.name, collection_names)
        self.assertIn("Test Collection 2", collection_names)

    def test_collection_detail(self):
        response = self.client.get(f"/api/collection/{self.collection.id}/")
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["id"], self.collection.id)
        self.assertEqual(data["name"], self.collection.name)

    def test_collection_create(self):
        response = self.client.post(
            "/api/collection/",
            {"name": "New Collection", "unlimited_regex": "http://test.com/.*"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "New Collection")
        self.assertEqual(data["unlimited_regex"], "http://test.com/.*")
        self.assertEqual(data["unlimited_regex_pg"], "http://test.com/.*")

    def test_collection_update(self):
        response = self.client.patch(
            f"/api/collection/{self.collection2.id}/",
            {"name": "Updated Collection", "unlimited_regex": "http://updated.com/.*\nhttp://other.com/.*"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "Updated Collection")
        self.assertEqual(data["unlimited_regex"], "http://updated.com/.*\nhttp://other.com/.*")
        self.assertEqual(data["unlimited_regex_pg"], "(http://updated.com/.*|http://other.com/.*)")

    def test_collection_delete(self):
        new_collection = Collection.objects.create(name="To Delete", unlimited_regex="http://delete.com/.*")
        response = self.client.delete(f"/api/collection/{new_collection.id}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(Collection.objects.filter(id=new_collection.id).exists())

    def test_collection_create_with_tags_webhooks(self):
        response = self.client.post(
            "/api/collection/",
            {
                "name": "Collection with Relations",
                "unlimited_regex": "http://test.com/.*",
                "tags": [self.tag.id, self.subtag.id],
                "webhooks": [self.test_webhook.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["name"], "Collection with Relations")
        self.assertEqual(sorted(data["tags"]), sorted([self.tag.id, self.subtag.id]))
        self.assertEqual(data["webhooks"], [self.test_webhook.id])

    def test_collection_update_tags_webhooks(self):
        response = self.client.patch(
            f"/api/collection/{self.collection2.id}/",
            {"tags": [self.subtag.id], "webhooks": [self.test_webhook.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["tags"], [self.subtag.id])
        self.assertEqual(data["webhooks"], [self.test_webhook.id])

    def test_queue_urls_basic(self):
        initial_count = Document.objects.count()
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://newsite.com/page1", "http://newsite.com/page2"],
                "collection": self.collection.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["message"], "2 URLs queued successfully")
        self.assertEqual(len(data["queued_urls"]), 2)
        self.assertIn("http://newsite.com/page1", data["queued_urls"])
        self.assertIn("http://newsite.com/page2", data["queued_urls"])
        self.assertEqual(data["collection"], self.collection.id)
        self.assertEqual(Document.objects.count(), initial_count + 2)

    def test_queue_urls_unlimited_scope(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://newsite.com/page"],
                "collection": self.collection.id,
                "crawl_scope": "unlimited",
                "show_on_homepage": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        self.assertEqual(data["crawl_scope"], "unlimited")
        self.assertEqual(data["show_on_homepage"], False)

        self.collection.refresh_from_db()
        self.assertIn("^https?://newsite\\.com/.*", self.collection.unlimited_regex)

    def test_queue_urls_limited_scope(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://testsite.org/"],
                "collection": self.collection.id,
                "crawl_scope": "limited",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        self.collection.refresh_from_db()
        self.assertIn("^https?://testsite\\.org/.*", self.collection.limited_regex)

    def test_queue_urls_invalid_url(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["not-a-valid-url", "http://valid.com"],
                "collection": self.collection.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("urls", data)

    def test_queue_urls_nonexistent_collection(self):
        response = self.client.post(
            "/api/queue/",
            {
                "urls": ["http://test.com"],
                "collection": 99999,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = json.loads(response.content)
        self.assertIn("collection", data)
