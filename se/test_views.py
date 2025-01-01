# Copyright 2022-2025 Laurent Defert
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

from urllib.parse import quote
import os

from django.conf import settings
from django.template.response import SimpleTemplateResponse
from django.test import TransactionTestCase
from django.utils import timezone

from se.atom import AtomView
from se.browser import ChromiumBrowser, FirefoxBrowser
from se.cached import CacheRedirectView
from se.document import Document
from se.download import DownloadView
from se.html import HTMLView, HTMLExcludedView
from se.models import CrawlerStats, CrawlPolicy, DomainSetting
from se.online import OnlineCheckView
from se.screenshot import ScreenshotView, ScreenshotFullView
from se.test_views_mixin import ViewsTestMixin
from se.views import (
    AboutView,
    HistoryView,
    OpensearchView,
    PreferencesView,
    SearchView,
    SearchRedirectView,
    WordStatsView,
)
from se.words import WordsView
from se.www import WWWView


CRAWL_URL = "http://127.0.0.1:8000/cookies"


class ViewsTest:
    def setUp(self):
        super().setUp()
        self.crawl_policy = CrawlPolicy.create_default()
        self.crawl_policy.default_browse_mode = self.BROWSER
        self.crawl_policy.take_screenshots = True
        self.crawl_policy.screenshot_format = Document.SCREENSHOT_PNG
        self.crawl_policy.save()
        self.doc = Document.objects.create(url=CRAWL_URL)
        Document.crawl(0)
        CrawlerStats.create(timezone.now())

    @classmethod
    def tearDownClass(cls):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()
        try:
            os.unlink(
                settings.SOSSE_HTML_SNAPSHOT_DIR
                + "http,3A/127.0.0.1,3A8000/cookies_98ba5952821ca60c491fa81c6214e26f.html"
            )
        except OSError:
            pass
        try:
            os.rmdir(settings.SOSSE_HTML_SNAPSHOT_DIR + "http,3A/127.0.0.1,3A8000/")
            os.rmdir(settings.SOSSE_HTML_SNAPSHOT_DIR + "http,3A/")
        except OSError:
            pass

    def test_views(self):
        for url, view_cls, kwargs in (
            ("/?q=page", SearchView, {}),
            ("/about/", AboutView, {}),
            ("/prefs/", PreferencesView, {}),
            ("/history/", HistoryView, {}),
            ("/?q=page", SearchView, {}),
            ("/s/?q=page", SearchRedirectView, {}),
            ("/atom/?q=page", AtomView, {}),
            ("/atom/?q=page&cached=1", AtomView, {}),
            ("/word_stats/?q=page", WordStatsView, {}),
            ("/opensearch.xml", OpensearchView, {}),
            ("/html/" + CRAWL_URL, HTMLView, {}),
            ("/www/" + CRAWL_URL, WWWView, {}),
            ("/www/http://unknown/", WWWView, {}),
            ("/words/" + CRAWL_URL, WordsView, {}),
            ("/download/" + CRAWL_URL, DownloadView, {}),
            ("/screenshot/" + CRAWL_URL, ScreenshotView, {}),
            ("/screenshot_full/" + CRAWL_URL, ScreenshotFullView, {}),
            ("/online_check/" + CRAWL_URL, OnlineCheckView, {}),
            (
                f"/html_excluded/{self.crawl_policy.id}/url",
                HTMLExcludedView,
                {"crawl_policy": self.crawl_policy.id, "method": "url"},
            ),
        ):
            view = view_cls.as_view()
            request = self._request_from_factory(url)
            try:
                response = view(request, **kwargs)
                if isinstance(response, SimpleTemplateResponse):
                    response.render()
            except:  # noqa
                raise Exception(f"Failed on {url}")
            self.assertEqual(
                response.status_code,
                200,
                f"{url}\n{response.content}\n{response.headers}",
            )

    def test_new_urls(self):
        from sosse.urls import urlpatterns

        self.assertEqual(len(urlpatterns), 25)

    def test_cache_redirect(self):
        request = self._request_from_factory("/cache/" + CRAWL_URL)
        response = CacheRedirectView.as_view()(request)
        self.assertEqual(response.status_code, 302, response)
        self.assertEqual(response.url, "/screenshot/" + CRAWL_URL, response)

    def test_admin_views(self):
        for url in (
            "/admin/",
            "/admin/se/document/queue/",
            "/admin/se/document/crawl_status/",
            "/admin/se/document/crawl_status_content/",
            "/admin/se/crawlpolicy/",
            f"/admin/se/crawlpolicy/{self.crawl_policy.id}/change/",
            "/admin/se/document/",
            "/admin/se/document/?queued=new",
            "/admin/se/document/?queued=pending",
            "/admin/se/document/?queued=recurring",
            "/admin/se/document/?has_error=yes",
            "/admin/se/document/?has_error=no",
            f"/admin/se/document/{self.doc.id}/change/",
            "/admin/se/domainsetting/",
            f"/admin/se/domainsetting/{DomainSetting.get_from_url(CRAWL_URL).id}/change/",
            "/admin/se/cookie/",
            f"/admin/se/cookie/?q={quote(CRAWL_URL)}",
            "/admin/se/excludedurl/",
            "/admin/se/searchengine/",
            "/admin/se/searchengine/?conflict=yes",
            "/admin/se/htmlasset/",
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"{url} / {response}")

    def test_admin_doc_actions(self):
        for action in ("remove_from_crawl_queue", "convert_to_jpg"):
            response = self.client.post(f"/admin/se/document/{self.doc.id}/do_action/", {"action": action})
            self.assertEqual(response.status_code, 302, f"{action} / {response}")
            self.assertEqual(
                response.url,
                f"/admin/se/document/{self.doc.id}/change/",
                f"{action} / {response}",
            )

        response = self.client.post(f"/admin/se/document/{self.doc.id}/do_action/", {"action": "crawl_now"})
        self.assertEqual(response.status_code, 302, f"{action} / {response}")
        self.assertEqual(
            response.url,
            "/admin/se/document/crawl_status/",
            f"{action} / {response}",
        )

    def test_admin_crawl_status_actions(self):
        for action in ("pause", "resume"):
            response = self.client.post("/admin/se/document/crawl_status/", {action: "1"})
            self.assertEqual(response.status_code, 200, f"{action} / {response}")

    def test_admin_add_crawl(self):
        response = self.client.post("/admin/se/document/queue_confirm/", {"url": CRAWL_URL})
        self.assertEqual(response.status_code, 200, response)

        response = self.client.post("/admin/se/document/queue_confirm/", {"url": CRAWL_URL, "action": "Confirm"})
        self.assertEqual(response.status_code, 302, response)


class ChromiumViewTest(ViewsTestMixin, ViewsTest, TransactionTestCase):
    BROWSER = DomainSetting.BROWSE_CHROMIUM


class FirefoxViewTest(ViewsTestMixin, ViewsTest, TransactionTestCase):
    BROWSER = DomainSetting.BROWSE_FIREFOX
