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

from datetime import datetime, timedelta, timezone
from hashlib import md5
from unittest import mock

from django.test import TransactionTestCase, override_settings
from feedparser import parse

from .browser import AuthElemFailed, SkipIndexing
from .crawl_policy import CrawlPolicy
from .document import Document
from .domain_setting import DomainSetting
from .models import ExcludedUrl, Link, WorkerStats
from .page import Page
from .test_mock import BrowserMock


class CrawlerTest(TransactionTestCase):
    DEFAULT_GETS = [
        mock.call("http://127.0.0.1/robots.txt", check_status=True),
        mock.call("http://127.0.0.1/"),
        mock.call("http://127.0.0.1/favicon.ico", check_status=True),
    ]

    def setUp(self):
        self.root_policy = CrawlPolicy.objects.create(
            url_regex="(default)",
            url_regex_pg=".*",
            recursion=CrawlPolicy.CRAWL_NEVER,
            default_browse_mode=DomainSetting.BROWSE_REQUESTS,
            snapshot_html=False,
            thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )
        self.crawl_policy = CrawlPolicy.objects.create(
            url_regex="http://127.0.0.1/",
            recursion=CrawlPolicy.CRAWL_ALL,
            default_browse_mode=DomainSetting.BROWSE_REQUESTS,
            snapshot_html=False,
            thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )
        self.fake_now = datetime(2000, 1, 1, tzinfo=timezone.utc)
        self.fake_yesterday = self.fake_now - timedelta(days=1)
        self.fake_next = datetime(2000, 1, 1, 1, tzinfo=timezone.utc)
        self.fake_next2 = datetime(2000, 1, 1, 3, tzinfo=timezone.utc)
        self.fake_next3 = datetime(2000, 1, 1, 6, tzinfo=timezone.utc)

    def tearDown(self):
        self.root_policy.delete()
        self.crawl_policy.delete()

    def _crawl(self, url="http://127.0.0.1/"):
        # Force create the worker
        WorkerStats.get_worker(0)

        Document.queue(url, None, None)
        while Document.crawl(0):
            pass

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_001_hello_world(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self._crawl()
        self.assertTrue(
            BrowserRequest.call_args_list == self.DEFAULT_GETS,
            BrowserRequest.call_args_list,
        )

        domain_setting = DomainSetting.objects.get()
        self.assertEqual(domain_setting.browse_mode, DomainSetting.BROWSE_REQUESTS)
        self.assertEqual(domain_setting.domain, "127.0.0.1")
        self.assertEqual(domain_setting.robots_status, DomainSetting.ROBOTS_EMPTY)

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_recurse, 0)
        self.assertFalse(doc.hidden)

        self.assertEqual(Link.objects.count(), 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_002_link_follow(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b'Root <a href="/page1/">Link1</a>',
                "http://127.0.0.1/page1/": b'Page1 <a href="http://127.0.0.2/">Link1</a>',
                "http://127.0.0.2/": b'No 2  <a href="http://127.0.0.2/">No 2 Link2</a>',
            }
        )
        self._crawl()
        self.assertTrue(
            BrowserRequest.call_args_list == self.DEFAULT_GETS + [mock.call("http://127.0.0.1/page1/")],
            BrowserRequest.call_args_list,
        )

        self.assertEqual(Document.objects.count(), 2)
        docs = Document.objects.w_content().order_by("id")
        self.assertEqual(docs[0].url, "http://127.0.0.1/")
        self.assertEqual(docs[0].content, "Root Link1")
        self.assertEqual(docs[0].crawl_recurse, 0)
        self.assertEqual(docs[1].url, "http://127.0.0.1/page1/")
        self.assertEqual(docs[1].content, "Page1 Link1")
        self.assertEqual(docs[1].crawl_recurse, 0)

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, docs[0])
        self.assertEqual(link.doc_to, docs[1])
        self.assertEqual(link.text, "Link1")
        self.assertEqual(link.pos, 5)
        self.assertEqual(link.link_no, 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_003_recursion_depth(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b'Root <a href="/page1/">Link1</a>',
                "http://127.0.0.1/page1/": b'Page1 <a href="http://127.0.0.2/">Link1</a><a href="http://127.0.0.3/">Link3</a>',
                "http://127.0.0.2/": b'No 2  <a href="http://127.0.0.2/page1/">No 2 Link1</a><a href="http://127.0.0.3/">Link3</a>',
                "http://127.0.0.2/page1/": b'Page2 <a href="http://127.0.0.2/page2/">No 2 Link2</a>',
                "http://127.0.0.2/page2/": b"No 2 - Page2",
                "http://127.0.0.3/": b"Page3",
            }
        )
        self.crawl_policy.recursion_depth = 2
        self.crawl_policy.save()

        CrawlPolicy.objects.create(
            url_regex="http://127.0.0.2/.*",
            recursion=CrawlPolicy.CRAWL_ON_DEPTH,
            default_browse_mode=DomainSetting.BROWSE_REQUESTS,
            snapshot_html=False,
            thumbnail_mode=CrawlPolicy.THUMBNAIL_MODE_NONE,
            take_screenshots=False,
        )
        self._crawl()

        self.assertTrue(
            BrowserRequest.call_args_list
            == self.DEFAULT_GETS
            + [
                mock.call("http://127.0.0.1/page1/"),
                mock.call("http://127.0.0.2/robots.txt", check_status=True),
                mock.call("http://127.0.0.2/"),
                mock.call("http://127.0.0.2/favicon.ico", check_status=True),
                mock.call("http://127.0.0.2/page1/"),
            ],
            BrowserRequest.call_args_list,
        )

        self.assertEqual(Document.objects.count(), 4)
        docs = Document.objects.w_content().order_by("id")
        self.assertEqual(docs[0].url, "http://127.0.0.1/")
        self.assertEqual(docs[0].content, "Root Link1")
        self.assertEqual(docs[0].crawl_recurse, 0)
        self.assertEqual(docs[1].url, "http://127.0.0.1/page1/")
        self.assertEqual(docs[1].content, "Page1 Link1 Link3")
        self.assertEqual(docs[1].crawl_recurse, 0)
        self.assertEqual(docs[2].url, "http://127.0.0.2/")
        self.assertEqual(docs[2].content, "No 2 No 2 Link1 Link3")
        self.assertEqual(docs[2].crawl_recurse, 2)
        self.assertEqual(docs[3].url, "http://127.0.0.2/page1/")
        self.assertEqual(docs[3].content, "Page2 No 2 Link2")
        self.assertEqual(docs[3].crawl_recurse, 1)

        self.assertEqual(Link.objects.count(), 3)
        links = Link.objects.order_by("id")
        self.assertEqual(links[0].doc_from, docs[0])
        self.assertEqual(links[0].doc_to, docs[1])
        self.assertEqual(links[0].text, "Link1")
        self.assertEqual(links[0].pos, 5)
        self.assertEqual(links[0].link_no, 0)
        self.assertEqual(links[1].doc_from, docs[1])
        self.assertEqual(links[1].doc_to, docs[2])
        self.assertEqual(links[1].text, "Link1")
        self.assertEqual(links[1].pos, 6)
        self.assertEqual(links[1].link_no, 0)
        self.assertEqual(links[2].doc_from, docs[2])
        self.assertEqual(links[2].doc_to, docs[3])
        self.assertEqual(links[2].text, "No 2 Link1")
        self.assertEqual(links[2].pos, 5)
        self.assertEqual(links[2].link_no, 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_004_extern_links(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b'Root <a href="/page1/">Link1</a>',
                "http://127.0.0.1/page1/": b"Page1",
            }
        )
        self.crawl_policy.store_extern_links = True
        self.crawl_policy.save()
        CrawlPolicy.objects.create(url_regex="http://127.0.0.1/page1/", recursion=CrawlPolicy.CRAWL_NEVER)
        self._crawl()
        self.assertTrue(
            BrowserRequest.call_args_list == self.DEFAULT_GETS,
            BrowserRequest.call_args_list,
        )

        self.assertEqual(Document.objects.count(), 1)
        docs = Document.objects.w_content().order_by("id")
        self.assertEqual(docs[0].url, "http://127.0.0.1/")
        self.assertEqual(docs[0].content, "Root Link1")
        self.assertEqual(docs[0].crawl_recurse, 0)

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, docs[0])
        self.assertEqual(link.doc_to, None)
        self.assertEqual(link.text, "Link1")
        self.assertEqual(link.pos, 5)
        self.assertEqual(link.link_no, 0)
        self.assertEqual(link.extern_url, "http://127.0.0.1/page1/")

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_005_recrawl_none(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        now.side_effect = lambda: self.fake_now
        self.crawl_policy.recrawl_freq = CrawlPolicy.RECRAWL_FREQ_NONE
        self.crawl_policy.recrawl_dt_min = None
        self.crawl_policy.recrawl_dt_max = None
        self.crawl_policy.save()

        self._crawl()
        self.assertTrue(
            BrowserRequest.call_args_list == self.DEFAULT_GETS,
            BrowserRequest.call_args_list,
        )

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_first, self.fake_now)
        self.assertEqual(doc.crawl_last, self.fake_now)
        self.assertEqual(doc.crawl_next, None)
        self.assertEqual(doc.crawl_dt, None)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_006_recrawl_constant(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.recrawl_freq = CrawlPolicy.RECRAWL_FREQ_CONSTANT
        self.crawl_policy.recrawl_dt_min = timedelta(hours=1)
        self.crawl_policy.recrawl_dt_max = None
        self.crawl_policy.save()

        now.side_effect = lambda: self.fake_now
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_first, self.fake_now)
        self.assertEqual(doc.crawl_last, self.fake_now)
        self.assertEqual(doc.crawl_next, self.fake_next)
        self.assertEqual(doc.crawl_dt, None)

        now.side_effect = lambda: self.fake_next
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_first, self.fake_now)
        self.assertEqual(doc.crawl_last, self.fake_next)
        self.assertEqual(doc.crawl_next, self.fake_next + timedelta(hours=1))
        self.assertEqual(doc.crawl_dt, None)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_007_recrawl_adaptive(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.recrawl_freq = CrawlPolicy.RECRAWL_FREQ_ADAPTIVE
        self.crawl_policy.recrawl_dt_min = timedelta(hours=1)
        self.crawl_policy.recrawl_dt_max = timedelta(hours=3)
        self.crawl_policy.save()

        now.side_effect = lambda: self.fake_now
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_first, self.fake_now)
        self.assertEqual(doc.crawl_last, self.fake_now)
        self.assertEqual(doc.crawl_next, self.fake_next)
        self.assertEqual(doc.crawl_dt, timedelta(hours=1))

        now.side_effect = lambda: self.fake_next
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_first, self.fake_now)
        self.assertEqual(doc.crawl_last, self.fake_next)
        self.assertEqual(doc.crawl_next, self.fake_next2)
        self.assertEqual(doc.crawl_dt, timedelta(hours=2))

        now.side_effect = lambda: self.fake_next2
        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "Hello world")
        self.assertEqual(doc.crawl_first, self.fake_now)
        self.assertEqual(doc.crawl_last, self.fake_next2)
        self.assertEqual(doc.crawl_next, self.fake_next3)
        self.assertEqual(doc.crawl_dt, timedelta(hours=3))

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_008_base_header(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b"""
                <html>
                    <head><base href="/base/" /></head>
                    <body>
                        <a href="test">base test</a>
                    </body>
                </html>
                """,
                "http://127.0.0.1/base/test": b"test page",
            }
        )

        self._crawl()

        self.assertEqual(Document.objects.count(), 2)
        doc1, doc2 = Document.objects.w_content().order_by("id")
        self.assertEqual(doc1.url, "http://127.0.0.1/")
        self.assertEqual(doc1.content, "base test")
        self.assertEqual(doc2.url, "http://127.0.0.1/base/test")
        self.assertEqual(doc2.content, "test page")

    @override_settings(TEST_MODE=False)
    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_010_generic_exception_handling(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": Exception("Generic exception")})

        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "")
        self.assertIn("Generic exception", doc.error)
        self.assertIn("Traceback (most recent call last):", doc.error)

    @override_settings(TEST_MODE=False)
    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_020_skip_exception_handling(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": SkipIndexing("Skip test")})

        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "")
        self.assertIn("Skip test", doc.error)
        self.assertNotIn("Traceback (most recent call last):", doc.error)

    @override_settings(TEST_MODE=False)
    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_030_auth_failed_exception_handling(self, BrowserRequest):
        page = Page("http://127.0.0.1/", b"test", BrowserMock)
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": AuthElemFailed(page, "xxx not found")})

        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "")
        self.assertIn("xxx not found", doc.error)
        self.assertNotIn("Traceback (most recent call last):", doc.error)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_040_extern_url_update(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b'<html><body><a href="/extern.html">extern link</a></body></html>',
                "http://127.0.0.1/extern.html": b"<html><body>extern page</body></html>",
            }
        )

        self.crawl_policy.url_regex = "http://127.0.0.1/$"
        self.crawl_policy.url_regex_pg = "http://127.0.0.1/$"
        self.crawl_policy.store_extern_links = True
        self.crawl_policy.save()

        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "extern link")

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, doc)
        self.assertIsNone(link.doc_to)
        self.assertEqual(link.extern_url, "http://127.0.0.1/extern.html")

        self.crawl_policy.url_regex = "http://127.0.0.1/.*$"
        self.crawl_policy.url_regex_pg = "http://127.0.0.1/.*$"
        self.crawl_policy.save()

        self._crawl("http://127.0.0.1/extern.html")

        self.assertEqual(Document.objects.count(), 2)
        doc1 = Document.objects.w_content().order_by("id").first()
        self.assertEqual(doc1.url, "http://127.0.0.1/")
        self.assertEqual(doc1.content, "extern link")
        doc2 = Document.objects.w_content().order_by("id").last()
        self.assertEqual(doc2.url, "http://127.0.0.1/extern.html")
        self.assertEqual(doc2.content, "extern page")

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, doc1)
        self.assertEqual(link.doc_to, doc2)
        self.assertIsNone(link.extern_url)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_050_binary_indexing(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({})
        self.crawl_policy.mimetype_regex = ".*"
        self.crawl_policy.save()
        self._crawl("http://127.0.0.1/image.png")

    MAILTO = {"http://127.0.0.1/": b'<body><a href="mailto:test@exemple.com">mail</a></body>'}

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_060_invalid_scheme(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(self.MAILTO)
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "mail")
        self.assertEqual(Link.objects.count(), 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_070_unknown_scheme_store(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(self.MAILTO)
        self.crawl_policy.store_extern_links = True
        self.crawl_policy.save()
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "mail")

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, doc)
        self.assertEqual(link.text, "mail")
        self.assertEqual(link.extern_url, "mailto:test@exemple.com")

    INVALID_LINK = {"http://127.0.0.1/": b'<body><a href="http://[invalid IPV6/">link</a></body>'}

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_090_invalid_link(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(self.INVALID_LINK)
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "link")
        self.assertEqual(Link.objects.count(), 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_100_invalid_link_store(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(self.INVALID_LINK)
        self.crawl_policy.store_extern_links = True
        self.crawl_policy.save()
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertEqual(doc.content, "link")

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, doc)
        self.assertEqual(link.text, "link")
        self.assertEqual(link.extern_url, "http://[invalid IPV6/")

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_110_excluded_url(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {"http://127.0.0.1/": b'<html><body><a href="/page.html">link</a></body></html>'}
        )
        ExcludedUrl.objects.create(url="http://127.0.0.1/page.html")
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_120_excluded_url_starts_with(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b'<html><body><a href="/no/exclude.html">link</a><a href="/page.html">link</a></body></html>'
            }
        )
        ExcludedUrl.objects.create(url="http://127.0.0.1/no/", starting_with=True)
        self._crawl()

        self.assertEqual(Document.objects.count(), 2)
        urls = Document.objects.wo_content().values_list("url", flat=True).order_by("url")
        self.assertEqual(list(urls), ["http://127.0.0.1/", "http://127.0.0.1/page.html"])

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_130_reschedule_no_change(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"<html><body>aaa 42</body></html>"})
        self.crawl_policy.recrawl_freq = CrawlPolicy.RECRAWL_FREQ_ADAPTIVE
        self.crawl_policy.recrawl_dt_min = timedelta(hours=1)
        self.crawl_policy.recrawl_dt_max = timedelta(hours=3)
        self.crawl_policy.save()

        now.side_effect = lambda: self.fake_now
        self._crawl()
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "aaa 42")
        self.assertEqual(doc.crawl_dt, timedelta(hours=1))

        BrowserRequest.side_effect = BrowserMock(
            {"http://127.0.0.1/": b"<html><body><!-- content unchanged -->aaa 24</body></html>"}
        )
        now.side_effect = lambda: self.fake_next
        self._crawl()
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "aaa 24")
        self.assertEqual(doc.crawl_dt, timedelta(hours=2))

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_140_reschedule_with_change(self, now, BrowserRequest):
        self.test_130_reschedule_no_change()

        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"<html><body>bbb</body></html>"})

        now.side_effect = lambda: self.fake_next2
        self._crawl()
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "bbb")
        self.assertEqual(doc.crawl_dt, timedelta(hours=1))

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_150_link_nested_text(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/": b'Root <a href="/page1/"><span>Nested</span></a>',
                "http://127.0.0.1/page1/": b"Page1",
            }
        )
        self._crawl()
        self.assertTrue(
            BrowserRequest.call_args_list == self.DEFAULT_GETS + [mock.call("http://127.0.0.1/page1/")],
            BrowserRequest.call_args_list,
        )

        self.assertEqual(Document.objects.count(), 2)
        docs = Document.objects.w_content().order_by("id")
        self.assertEqual(docs[0].url, "http://127.0.0.1/")
        self.assertEqual(docs[0].content, "Root Nested")
        self.assertEqual(docs[0].crawl_recurse, 0)
        self.assertEqual(docs[1].url, "http://127.0.0.1/page1/")
        self.assertEqual(docs[1].content, "Page1")
        self.assertEqual(docs[1].crawl_recurse, 0)

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, docs[0])
        self.assertEqual(link.doc_to, docs[1])
        self.assertEqual(link.text, "Nested")
        self.assertEqual(link.pos, 5)
        self.assertEqual(link.link_no, 0)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_160_hidden(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.hide_documents = True
        self.crawl_policy.save()

        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.wo_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertTrue(doc.hidden)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_170_policy_disabled(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.root_policy.hide_documents = True
        self.root_policy.save()
        self.crawl_policy.enabled = False
        self.crawl_policy.save()

        self._crawl()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.wo_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")
        self.assertTrue(doc.hidden)

    def _test_modification_base(self):
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.wo_content().get()
        self.assertEqual(doc.url, "http://127.0.0.1/")

        # Mark the document as modified in the past
        doc.modified_date = self.fake_yesterday

        # Force crawl_next to make it crawled again when calling self._crawl()
        doc.crawl_next = self.fake_yesterday
        doc.save()

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_180_modification_no_change(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world 1"})
        self.crawl_policy.hash_mode = CrawlPolicy.HASH_RAW
        self.crawl_policy.save()
        self._test_modification_base()

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "Hello world 1")
        self.assertEqual(doc.content_hash, md5(b"Hello world 1").hexdigest())
        self.assertEqual(doc.modified_date, self.fake_yesterday)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_190_modification_change(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world 1"})
        now.side_effect = lambda: self.fake_now
        self.crawl_policy.hash_mode = CrawlPolicy.HASH_RAW
        self.crawl_policy.save()
        self._test_modification_base()

        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world 2"})
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "Hello world 2")
        self.assertEqual(doc.content_hash, md5(b"Hello world 2").hexdigest())
        self.assertEqual(doc.modified_date, self.fake_now)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_200_modification_no_change_number_normalize(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world 1"})
        now.side_effect = lambda: self.fake_now
        self.crawl_policy.hash_mode = CrawlPolicy.HASH_NO_NUMBERS
        self.crawl_policy.save()
        self._test_modification_base()

        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world 2"})
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "Hello world 2")
        self.assertEqual(doc.content_hash, md5(b"Hello world 0").hexdigest())
        self.assertEqual(doc.modified_date, self.fake_yesterday)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_210_modification_change_number_normalize(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        now.side_effect = lambda: self.fake_now
        self._test_modification_base()

        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world change"})
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)

        doc = Document.objects.w_content().get()
        self.assertEqual(doc.content, "Hello world change")
        self.assertEqual(doc.content_hash, md5(b"Hello world change").hexdigest())
        self.assertEqual(doc.modified_date, self.fake_now)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_220_recrawl_cond_on_change__no_change(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self._test_modification_base()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(feedparser_parse.call_count, 1)

        self._crawl()
        self.assertEqual(feedparser_parse.call_count, 1)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_230_recrawl_cond_on_change__change(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self._test_modification_base()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(feedparser_parse.call_count, 1)

        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world change"})
        self._crawl()
        self.assertEqual(feedparser_parse.call_count, 2)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_240_recrawl_cond_always(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.recrawl_condition = CrawlPolicy.RECRAWL_COND_ALWAYS
        self.crawl_policy.save()

        self._test_modification_base()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(feedparser_parse.call_count, 1)

        self._crawl()
        self.assertEqual(feedparser_parse.call_count, 2)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_250_recrawl_cond_manual__change(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.recrawl_condition = CrawlPolicy.RECRAWL_COND_MANUAL
        self.crawl_policy.save()

        self._test_modification_base()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(feedparser_parse.call_count, 1)

        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world change"})
        self._crawl()
        self.assertEqual(feedparser_parse.call_count, 2)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_260_recrawl_cond_manual__no_change(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.recrawl_condition = CrawlPolicy.RECRAWL_COND_MANUAL
        self.crawl_policy.save()
        self._test_modification_base()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(feedparser_parse.call_count, 1)

        self._crawl()
        self.assertEqual(feedparser_parse.call_count, 1)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_270_recrawl_cond_manual__manual(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.recrawl_condition = CrawlPolicy.RECRAWL_COND_MANUAL
        self.crawl_policy.save()
        self._test_modification_base()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(feedparser_parse.call_count, 1)

        Document.objects.update(manual_crawl=True)
        self._crawl()

        self.assertEqual(feedparser_parse.call_count, 2)
        self.assertFalse(Document.objects.wo_content().get().manual_crawl)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("feedparser.parse", wraps=parse)
    def test_280_recrawl_keeps_tags(self, feedparser_parse, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        self.crawl_policy.tags.create(name="tag1")

        self.assertEqual(Document.objects.count(), 0)
        self._crawl()
        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.w_content().get()
        self.assertEqual(list(doc.tags.values_list("name", flat=True)), ["tag1"])

        doc.tags.create(name="tag2")
        self.assertEqual(list(doc.tags.values_list("name", flat=True)), ["tag1", "tag2"])

        self._crawl()
        doc = Document.objects.w_content().get()
        self.assertEqual(list(doc.tags.values_list("name", flat=True)), ["tag1", "tag2"])

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.document.now")
    def test_290_recrawl_new_pages_first(self, now, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({"http://127.0.0.1/": b"Hello world"})
        now.side_effect = lambda: self.fake_now

        self.crawl_policy.recrawl_freq = CrawlPolicy.RECRAWL_FREQ_NONE
        self.crawl_policy.save()

        already_crawled = Document.objects.create(
            url="http://127.0.0.1/page.html",
            content="done",
            crawl_last=self.fake_yesterday,
            crawl_next=self.fake_yesterday,
        )

        WorkerStats.get_worker(0)
        Document.queue("http://127.0.0.1/", None, None)
        Document.crawl(0)

        self.assertEqual(Document.objects.count(), 2)

        doc = Document.objects.w_content().get(url="http://127.0.0.1/")
        self.assertEqual(doc.crawl_last, self.fake_now)

        already_crawled.refresh_from_db()
        self.assertEqual(already_crawled.crawl_last, self.fake_yesterday)
        self.assertEqual(already_crawled.crawl_next, self.fake_yesterday)
