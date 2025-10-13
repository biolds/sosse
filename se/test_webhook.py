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

import json
from datetime import timedelta
from unittest import mock

from django.test import TransactionTestCase
from django.utils.timezone import now

from sosse.conf import DEFAULT_USER_AGENT

from .browser import SkipIndexing
from .collection import Collection
from .document import Document, example_doc
from .domain import Domain
from .models import WorkerStats
from .tag import Tag
from .test_functionals import TEST_SERVER_URL
from .test_mock import BrowserMock
from .webhook import Webhook


class WebhookTest(TransactionTestCase):
    maxDiff = None

    def setUp(self):
        self.collection = Collection.objects.create(
            name="Test Collection",
            default_browse_mode=Domain.BROWSE_REQUESTS,
            snapshot_html=False,
            thumbnail_mode=Collection.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )
        self.webhook = Webhook.objects.create(
            name="Test Webhook",
            url=f"{TEST_SERVER_URL}post",
            method="post",
            headers="",
            body_template='{"content": "${content}", "title": "${title}"}',
        )
        self.document = example_doc()
        self.document.collection = self.collection
        self.document.metadata = {"key": "value"}
        self.document.save()
        self.collection.webhooks.add(self.webhook)
        self.tag = Tag.objects.create(name="Test")
        self.tag_child = Tag.objects.create(name="Test Child", parent=self.tag)
        self.collection.tags.add(self.tag_child)

    def _check_render(self, doc, expected):
        body = self.webhook._render_template(doc, self.webhook.body_template)
        body_dict = json.loads(body)
        self.assertEqual(body_dict, expected)

    def test_010_render(self):
        self._check_render(self.document, {"content": "Example", "title": "Example Title"})

    def test_020_render_bool(self):
        self.webhook.body_template = '{"too_many_redirects": "${too_many_redirects}"}'
        self._check_render(self.document, {"too_many_redirects": "False"})

    def test_030_render_int(self):
        self.webhook.body_template = '{"screenshot_count": "${screenshot_count}"}'
        self._check_render(self.document, {"screenshot_count": "0"})

    def test_040_render_multi(self):
        self.webhook.body_template = '{"title & url": "${title} - ${url}"}'
        self._check_render(self.document, {"title & url": "Example Title - https://example.com/"})

    def test_045_render_tags(self):
        self.document.tags.add(self.tag, self.tag_child)
        self.webhook.body_template = '{"tags_str": "${tags_str}"}'
        self._check_render(self.document, {"tags_str": "Test, Test Child"})

    def test_050_render_recursive(self):
        self.webhook.body_template = '{"parent": {"title": "${title}", "content": "${content}"}}'
        self._check_render(self.document, {"parent": {"title": "Example Title", "content": "Example"}})

    def test_055_render_recursive_list(self):
        self.webhook.body_template = '{"parent": [{"sub": {"title": "${title}", "content": "${content}"}}]}'
        self._check_render(self.document, {"parent": [{"sub": {"title": "Example Title", "content": "Example"}}]})

    def test_057_render_dotted_var(self):
        self.webhook.body_template = '{"key": "${metadata.key}"}'
        self._check_render(self.document, {"key": "value"})

    def _assert_post(self, post, _headers={}, _params={}):
        post.assert_called_once_with(
            self.webhook.url,
            data='{"content": "Example", "title": "Example Title"}',
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            | _headers,
            timeout=10,
            **_params,
        )

    @mock.patch("se.webhook.requests.post")
    def test_060_send_webhook(self, post):
        post.side_effect = lambda *args, **kwargs: mock.Mock(status_code=200, reason="OK", text="{}")
        self.webhook.send(self.document)
        self._assert_post(post)

    def _crawl(self, change_content=False):
        with mock.patch("se.browser_request.BrowserRequest.get") as BrowserRequest:
            if change_content:
                BrowserRequest.side_effect = BrowserMock(
                    {"http://127.0.0.1/full_page.html": b"<html><body>Other content</body></html>"}
                )
            else:
                BrowserRequest.side_effect = BrowserMock({})

            # Force create the worker
            WorkerStats.get_worker(0)

            if self.document:
                self.document.delete()
                self.document = None
            Document.queue("http://127.0.0.1/full_page.html", self.collection, None)
            Document.crawl(0)
            self.assertEqual(Document.objects.count(), 1)
            doc = Document.objects.w_content().first()
            self.assertEqual(doc.url, "http://127.0.0.1/full_page.html")
            self.assertEqual(doc.title, "http://127.0.0.1/full_page.html")
            content = "Other content" if change_content else "Content"
            self.assertEqual(doc.content, content)
            self.assertIsNotNone(doc.crawl_first)
            self.assertFalse(doc.manual_crawl)
            return doc

    @mock.patch("se.webhook.requests.post")
    def test_070_send_custom_header(self, post):
        post.side_effect = lambda *args, **kwargs: mock.Mock(status_code=200, reason="OK", text="{}")
        self.webhook.headers = "X-Test: Test"
        self.webhook.send(self.document)
        self._assert_post(post, {"X-Test": "Test"})

    @mock.patch("se.webhook.requests.post")
    def test_080_send_auth(self, post):
        post.side_effect = lambda *args, **kwargs: mock.Mock(status_code=200, reason="OK", text="{}")
        self.webhook.username = "user"
        self.webhook.password = "pass"
        self.webhook.send(self.document)
        self._assert_post(post, _params={"auth": ("user", "pass")})

    def test_090_trigger_webhook(self):
        doc = self._crawl()

        result = doc.webhooks_result[str(self.webhook.id)]
        response = json.loads(result["response"])
        result["response"] = response["data"]

        self.assertDictEqual(
            result,
            {
                "error": None,
                "status_code": 200,
                "status_string": "OK",
                "response": '{"content": "Content", "title": "http://127.0.0.1/full_page.html"}',
            },
        )

    def _test_trigger(self, collection_cond, webhook_cond, expected_webhook_call_count, change_content=False):
        with mock.patch("se.webhook.requests.post") as post:
            post.side_effect = lambda *args, **kwargs: mock.Mock(status_code=200, reason="OK", text="{}")
            self.collection.recrawl_condition = collection_cond
            self.collection.save()
            self.webhook.trigger_condition = webhook_cond
            self.webhook.save()
            self._crawl(change_content)
            self.assertEqual(
                post.call_count, expected_webhook_call_count, f"failed with collection_cond {collection_cond}"
            )

            # Set crawl_next to force recrawl on next call
            Document.objects.update(crawl_next=now() - timedelta(seconds=1))

    def test_100_trigger_webhook_condition_discovery(self):
        for collection_cond in Collection.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_DISCOVERY, 1)
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_DISCOVERY, 0)

    def test_110_trigger_webhook_condition_on_change__no_change(self):
        for collection_cond in Collection.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 1)
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 0)

    def test_120_trigger_webhook_condition_on_change__with_change(self):
        for collection_cond in Collection.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 1)
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 1, change_content=True)

    def test_130_trigger_webhook_condition_always(self):
        for collection_cond in Collection.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_ALWAYS, 1)
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_ALWAYS, 1)

    def test_140_trigger_webhook_condition_manual(self):
        for collection_cond in Collection.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_MANUAL, 1)

            # No trigger on no change
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_MANUAL, 0)

            # Trigger when manual
            Document.objects.wo_content().update(manual_crawl=True)
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_MANUAL, 1)

            # Tiggers on change
            self._test_trigger(collection_cond[0], Webhook.TRIGGER_COND_MANUAL, 1, True)

    def test_150_trigger_webhook_no_regexp_match(self):
        self.webhook.content_re = "No match"
        self._test_trigger(Collection.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 0)

        self.webhook.content_re = "Content"
        self._test_trigger(Collection.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 1)

    def test_160_trigger_webhook_tag_match(self):
        self.webhook.tags.add(self.tag)
        self._test_trigger(Collection.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 1)

    def test_170_trigger_webhook_child_tag_match(self):
        self.webhook.tags.add(self.tag)
        self._test_trigger(Collection.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 1)

    def test_180_trigger_webhook_no_tag_match(self):
        self.collection.tags.clear()
        self.webhook.tags.add(self.tag)
        self._test_trigger(Collection.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 0)

    def test_190_update_document(self):
        self.webhook.updates_doc = True
        self.webhook.body_template = '{"tags": ["New tag"]}'
        self.webhook.url = f"{TEST_SERVER_URL}echo/"
        self.webhook.save()

        doc = self._crawl()

        self.assertEqual(doc.error, "")
        result = doc.webhooks_result[str(self.webhook.id)]
        self.assertEqual(result["status_code"], 200, result)
        self.assertEqual(result["response"], self.webhook.body_template)
        self.assertEqual(doc.tags.first().name, "New tag")

    def test_200_update_document_failure(self):
        self.webhook.updates_doc = True
        self.webhook.body_template = '{"tags": null}'
        self.webhook.url = f"{TEST_SERVER_URL}echo/"
        self.webhook.save()

        with self.assertRaises(SkipIndexing) as e:
            self._crawl()

        self.assertEqual(
            e.exception.args[0],
            """Webhook result validation error:
{'tags': [ErrorDetail(string='This field may not be null.', code='null')]}
Input data was:
{'tags': None}
---""",
        )

    def test_210_update_document_with_path(self):
        self.webhook.updates_doc = True
        self.webhook.update_json_path = "path.to"
        self.webhook.body_template = '{"path": {"to": {"metadata": {"key": "val"}}}}'
        self.webhook.url = f"{TEST_SERVER_URL}echo/"
        self.webhook.save()

        doc = self._crawl()

        self.assertEqual(doc.error, "")
        result = doc.webhooks_result[str(self.webhook.id)]
        self.assertEqual(result["status_code"], 200, result)
        self.assertEqual(result["response"], self.webhook.body_template)
        self.assertEqual(doc.metadata, {"key": "val"})

    def test_220_update_document_with_path_with_list(self):
        self.webhook.updates_doc = True
        self.webhook.update_json_path = "path.to.1"
        self.webhook.body_template = '{"path": {"to": ["nop", {"metadata": {"key": "val"}}]}}'
        self.webhook.url = f"{TEST_SERVER_URL}echo/"
        self.webhook.save()

        doc = self._crawl()

        self.assertEqual(doc.error, "")
        result = doc.webhooks_result[str(self.webhook.id)]
        self.assertEqual(result["status_code"], 200, result)
        self.assertEqual(result["response"], self.webhook.body_template)
        self.assertEqual(doc.metadata, {"key": "val"})

    def test_230_update_document_deserialize(self):
        self.webhook.updates_doc = True
        self.webhook.update_json_deserialize = True
        self.webhook.update_json_path = "sub"
        self.webhook.body_template = r'{"sub": "{\"metadata\":{\"key\": \"val\"}}"}'
        self.webhook.url = f"{TEST_SERVER_URL}echo/"
        self.webhook.save()

        doc = self._crawl()

        self.assertEqual(doc.error, "")
        result = doc.webhooks_result[str(self.webhook.id)]
        self.assertEqual(result["status_code"], 200, result)
        self.assertEqual(result["response"], self.webhook.body_template)
        self.assertEqual(doc.metadata, {"key": "val"})
