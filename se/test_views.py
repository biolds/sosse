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

import os
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import TransactionTestCase
from django.utils import timezone

from .about import AboutView
from .add_to_queue import AddToQueueView
from .analytics import AnalyticsView
from .archive import ArchiveRedirectView
from .atom import AtomView
from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .cookies_import import CookiesImportView
from .crawl_policy import CrawlPolicy
from .crawl_queue import CrawlQueueContentView, CrawlQueueView
from .crawlers import CrawlersContentView, CrawlersView
from .document import Document
from .domain_setting import DomainSetting
from .download import DownloadView
from .history import HistoryView
from .html import HTMLExcludedView, HTMLView
from .models import CrawlerStats
from .online import OnlineCheckView
from .opensearch import OpensearchView
from .preferences import PreferencesView
from .screenshot import ScreenshotFullView, ScreenshotView
from .search import SearchView
from .search_redirect import SearchRedirectView
from .test_cookies_import import NETSCAPE_COOKIE_HEADER, NOW_TIMESTAMP
from .test_views_mixin import ViewsTestMixin
from .words import WordsView
from .words_stats import WordStatsView
from .www import WWWView

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
        BrowserChromium.destroy()
        BrowserFirefox.destroy()
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
        for url, view_cls, params in (
            ("/?q=page", SearchView, {}),
            ("/about/", AboutView, {}),
            ("/prefs/", PreferencesView, {}),
            ("/history/", HistoryView, {}),
            ("/?q=page", SearchView, {}),
            ("/s/?q=page", SearchRedirectView, {}),
            ("/word_stats/?q=page", WordStatsView, {}),
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
            self._view_request(url, view_cls, params, self.admin_user, 200)
            self._view_request(url, view_cls, params, self.simple_user, 200)

            response = self._view_request(url, view_cls, params, self.anon_user, 302)
            self.assertTrue(response.headers.get("Location", "").startswith("/login/?next="))

            with self.settings(SOSSE_ANONYMOUS_SEARCH=True):
                self._view_request(url, view_cls, params, self.admin_user, 200)
                self._view_request(url, view_cls, params, self.simple_user, 200)
                anon_expected = 302 if url == "/history/" else 200
                self._view_request(url, view_cls, params, self.anon_user, anon_expected)

    def test_views_no_auth(self):
        """Test views that require no authentication."""
        for url, view_cls, params in (("/opensearch.xml", OpensearchView, {}),):
            for anon_search in (True, False):
                with self.settings(SOSSE_ANONYMOUS_SEARCH=anon_search):
                    self._view_request(url, view_cls, params, self.admin_user, 200)
                    self._view_request(url, view_cls, params, self.simple_user, 200)
                    self._view_request(url, view_cls, params, self.anon_user, 200)

    def test_views_no_auth_redirect(self):
        """Test views that do not redirect to the login page when auth is
        required."""
        for url, view_cls, params in (
            ("/atom/?q=page", AtomView, {}),
            ("/atom/?q=page&archive=1", AtomView, {}),
        ):
            for anon_search in (True, False):
                with self.settings(SOSSE_ANONYMOUS_SEARCH=anon_search):
                    self._view_request(url, view_cls, params, self.admin_user, 200)
                    self._view_request(url, view_cls, params, self.simple_user, 200)
                    anon_expected = 200 if anon_search else 403
                    self._view_request(url, view_cls, params, self.anon_user, anon_expected)

    def test_new_urls(self):
        from sosse.urls import urlpatterns

        self.assertEqual(len(urlpatterns), 25)

    def test_archive_redirect(self):
        request = self._request_from_factory("/archive/" + CRAWL_URL, self.admin_user)
        response = ArchiveRedirectView.as_view()(request)
        self.assertEqual(response.status_code, 302, response)
        self.assertEqual(response.url, "/screenshot/" + CRAWL_URL, response)

    def test_admin_views(self):
        for url, view_cls in (
            ("/admin/", None),
            ("/admin/se/document/queue/", AddToQueueView),
            ("/admin/se/document/crawl_queue/", CrawlQueueView),
            ("/admin/se/document/crawl_queue_content/", CrawlQueueContentView),
            ("/admin/se/document/crawlers/", CrawlersView),
            ("/admin/se/document/crawlers_content/", CrawlersContentView),
            ("/admin/se/crawlpolicy/", None),
            (f"/admin/se/crawlpolicy/{self.crawl_policy.id}/change/", None),
            ("/admin/se/document/", None),
            ("/admin/se/document/?queued=new", None),
            ("/admin/se/document/?queued=pending", None),
            ("/admin/se/document/?queued=recurring", None),
            ("/admin/se/document/?has_error=yes", None),
            ("/admin/se/document/?has_error=no", None),
            (f"/admin/se/document/{self.doc.id}/change/", None),
            ("/admin/se/document/analytics/", AnalyticsView),
            ("/admin/se/domainsetting/", None),
            (f"/admin/se/domainsetting/{DomainSetting.get_from_url(CRAWL_URL).id}/change/", None),
            ("/admin/se/cookie/", None),
            (f"/admin/se/cookie/?q={quote(CRAWL_URL)}", None),
            ("/admin/se/cookie/import/", CookiesImportView),
            ("/admin/se/excludedurl/", None),
            ("/admin/se/searchengine/", None),
            ("/admin/se/searchengine/?conflict=yes", None),
            ("/admin/se/htmlasset/", None),
        ):
            response = self.admin_client.get(url)
            self.assertEqual(response.status_code, 200, f"{url} / {response}")

            response = self.simple_client.get(url)
            self.assertEqual(response.status_code, 302, f"{url} / {response}")

            response = self.anon_client.get(url)
            self.assertEqual(response.status_code, 302, f"{url} / {response}")

            self.staff_user.user_permissions.clear()
            response = self.staff_client.get(url)

            if view_cls:
                permissions = view_cls.permission_required
                if isinstance(permissions, str):
                    permissions = {permissions}
            elif url == "/admin/":
                permissions = set()
            else:
                model_name = url.split("/")[3]
                permissions = {f"se.view_{model_name}"}

            if permissions:
                self.assertEqual(response.status_code, 403, f"{url} / {response}")

                permissions = {Permission.objects.get(codename=perm.split(".")[1]) for perm in permissions}
                self.staff_user.user_permissions.set(permissions)
                response = self.staff_client.get(url)

            self.assertEqual(response.status_code, 200, f"{url} / {response}")

    def test_admin_doc_actions(self):
        for action in ("remove_from_crawl_queue", "convert_to_jpg"):
            response = self.admin_client.post(f"/admin/se/document/{self.doc.id}/do_action/", {"action": action})
            self.assertEqual(response.status_code, 302, f"{action} / {response}")
            self.assertEqual(
                response.url,
                f"/admin/se/document/{self.doc.id}/change/",
                f"{action} / {response}",
            )

        response = self.admin_client.post(f"/admin/se/document/{self.doc.id}/do_action/", {"action": "crawl_now"})
        self.assertEqual(response.status_code, 302, f"{action} / {response}")
        self.assertEqual(
            response.url,
            "/admin/se/document/crawl_queue/",
            f"{action} / {response}",
        )

    def test_cookie_import_view(self):
        response = self.admin_client.get("/admin/se/cookie/import/")
        self.assertEqual(response.status_code, 200, response)

        response = self.admin_client.post(
            "/admin/se/cookie/import/",
            {"cookies": "cookie"},
        )
        self.assertEqual(response.status_code, 200, response)
        self.assertIn("does not look like a Netscape format cookies file", response.content.decode())

        response = self.admin_client.post(
            "/admin/se/cookie/import/",
            {"cookies": f"{NETSCAPE_COOKIE_HEADER}\n.test.com\tTRUE\t/\tFALSE\t{NOW_TIMESTAMP}\tname\tvalue"},
        )
        self.assertEqual(response.status_code, 302, response)
        self.assertEqual(response.headers["Location"], "/admin/se/cookie/")

    def test_admin_crawl_queue_actions(self):
        for action in ("pause", "resume"):
            response = self.admin_client.post("/admin/se/document/crawl_queue/", {action: "1"})
            self.assertEqual(response.status_code, 200, f"{action} / {response}")

            response = self.simple_client.post("/admin/se/document/crawl_queue/", {action: "1"})
            self.assertEqual(response.status_code, 302, f"{action} / {response}")

            self.staff_user.user_permissions.clear()
            response = self.staff_client.post("/admin/se/document/crawl_queue/", {action: "1"})
            self.assertEqual(response.status_code, 403, f"{action} without permission / {response}")

            permission = Permission.objects.get(codename="change_crawlerstats")
            self.staff_user.user_permissions.add(permission)
            response = self.staff_client.post("/admin/se/document/crawl_queue/", {action: "1"})
            self.assertEqual(response.status_code, 200, f"{action} with permission / {response}")


class ChromiumViewTest(ViewsTestMixin, ViewsTest, TransactionTestCase):
    BROWSER = DomainSetting.BROWSE_CHROMIUM


class FirefoxViewTest(ViewsTestMixin, ViewsTest, TransactionTestCase):
    BROWSER = DomainSetting.BROWSE_FIREFOX
