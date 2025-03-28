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

import json
from datetime import timedelta
from unittest import mock

from django.test import TransactionTestCase
from django.utils.timezone import now

from sosse.conf import DEFAULT_USER_AGENT

from .crawl_policy import CrawlPolicy
from .document import Document, example_doc
from .domain_setting import DomainSetting
from .models import WorkerStats
from .test_functionals import TEST_SERVER_URL
from .test_mock import BrowserMock
from .webhook import Webhook


class WebhookTest(TransactionTestCase):
    maxDiff = None

    def setUp(self):
        self.webhook = Webhook.objects.create(
            name="Test Webhook",
            url=f"{TEST_SERVER_URL}post",
            method="post",
            headers="",
            body_template='{"content": "$content", "title": "$title"}',
        )
        self.document = example_doc()
        self.document.save()
        self.crawl_policy = CrawlPolicy.objects.create(
            url_regex="(default)",
            url_regex_pg=".*",
            recursion=CrawlPolicy.CRAWL_NEVER,
            default_browse_mode=DomainSetting.BROWSE_REQUESTS,
            snapshot_html=False,
            thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )
        self.crawl_policy.webhooks.add(self.webhook)

    def _check_render(self, doc, expected):
        body = self.webhook._render_template(doc, self.webhook.body_template)
        body_dict = json.loads(body)
        self.assertEqual(body_dict, expected)

    def test_010_render(self):
        self._check_render(self.document, {"content": "Example", "title": "Example Title"})

    def test_020_render_bool(self):
        self.webhook.body_template = '{"too_many_redirects": "$too_many_redirects"}'
        self._check_render(self.document, {"too_many_redirects": "False"})

    def test_030_render_int(self):
        self.webhook.body_template = '{"screenshot_count": "$screenshot_count"}'
        self._check_render(self.document, {"screenshot_count": "0"})

    def test_040_render_multi(self):
        self.webhook.body_template = '{"title & url": "$title - $url"}'
        self._check_render(self.document, {"title & url": "Example Title - https://example.com/"})

    def test_050_render_recursive(self):
        self.webhook.body_template = '{"parent": {"title": "$title", "content": "$content"}}'
        self._check_render(self.document, {"parent": {"title": "Example Title", "content": "Example"}})

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
            Document.queue("http://127.0.0.1/full_page.html", None, None)
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

    def _test_trigger(self, crawl_policy_cond, webhook_cond, expected_webhook_call_count, change_content=False):
        with mock.patch("se.webhook.requests.post") as post:
            post.side_effect = lambda *args, **kwargs: mock.Mock(status_code=200, reason="OK", text="{}")
            self.crawl_policy.recrawl_condition = crawl_policy_cond
            self.crawl_policy.save()
            self.webhook.trigger_condition = webhook_cond
            self.webhook.save()
            self._crawl(change_content)
            self.assertEqual(
                post.call_count, expected_webhook_call_count, f"failed with crawl_policy_cond {crawl_policy_cond}"
            )

            # Set crawl_next to force recrawl on next call
            Document.objects.update(crawl_next=now() - timedelta(seconds=1))

    def test_100_trigger_webhook_condition_discovery(self):
        for crawl_policy_cond in CrawlPolicy.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_DISCOVERY, 1)
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_DISCOVERY, 0)

    def test_110_trigger_webhook_condition_on_change__no_change(self):
        for crawl_policy_cond in CrawlPolicy.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 1)
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 0)

    def test_120_trigger_webhook_condition_on_change__with_change(self):
        for crawl_policy_cond in CrawlPolicy.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 1)
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_ON_CHANGE, 1, change_content=True)

    def test_130_trigger_webhook_condition_always(self):
        for crawl_policy_cond in CrawlPolicy.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_ALWAYS, 1)
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_ALWAYS, 1)

    def test_140_trigger_webhook_condition_manual(self):
        for crawl_policy_cond in CrawlPolicy.RECRAWL_CONDITION:
            Document.objects.wo_content().delete()
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_MANUAL, 1)

            # No trigger on no change
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_MANUAL, 0)

            # Trigger when manual
            Document.objects.wo_content().update(manual_crawl=True)
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_MANUAL, 1)

            # Tiggers on change
            self._test_trigger(crawl_policy_cond[0], Webhook.TRIGGER_COND_MANUAL, 1, True)

    def test_150_trigger_webhook_no_regexp_match(self):
        self.webhook.content_re = "No match"
        self._test_trigger(CrawlPolicy.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 0)

        self.webhook.content_re = "Content"
        self._test_trigger(CrawlPolicy.RECRAWL_COND_ALWAYS, Webhook.TRIGGER_COND_ALWAYS, 1)
