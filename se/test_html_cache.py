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

from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.test import TransactionTestCase
from django.utils import timezone

from .collection import Collection
from .html_asset import HTMLAsset
from .html_cache import CacheHit, CacheMiss, HTMLCache
from .page import Page
from .test_html_snapshot import GET_EXPECTED_HEADERS
from .test_mock import BrowserMock
from .url import sanitize_url
from .utils import http_date_format


class HTMLCacheTest(TransactionTestCase):
    def setUp(self):
        self.collection = Collection.create_default()

    def test_010_html_filenames(self):
        for url, fn in (
            ("http://127.0.0.1/test.html", "http,3A/127.0.0.1/test.html_~~~.html"),
            (
                "http://127.0.0.1/test.html?a=b",
                "http,3A/127.0.0.1/test.html,3Fa,3Db_~~~.html",
            ),
            ("http://127.0.0.1/", "http,3A/127.0.0.1/_~~~.html"),
            ("http://127.0.0.1/../", "http,3A/127.0.0.1/_~~~.html"),
            ("http://127.0.0.1/,", "http,3A/127.0.0.1/,2C_~~~.html"),
        ):
            url = sanitize_url(url)
            _fn = HTMLCache.html_filename(url, "~~~", ".html")
            self.assertEqual(_fn, fn, f"failed on {url} / expected {fn} / got {_fn}")

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_020_cache_miss(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock({})
        assets_count = HTMLAsset.objects.count()
        self.assertEqual(assets_count, 0)

        with self.assertRaises(CacheMiss):
            HTMLCache._cache_check("http://127.0.0.1/image.png", self.collection, "http://127.0.0.1/", 0)

    def _download_miss(self, BrowserRequest):
        page = HTMLCache.download(
            "http://127.0.0.1/to_cache.png", self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE
        )
        HTMLCache.write_asset(page.url, page.content, page, mimetype=page.mimetype)

        self.assertTrue(
            BrowserRequest.call_args_list
            == [
                mock.call(
                    "http://127.0.0.1/to_cache.png",
                    self.collection,
                    check_status=True,
                    max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE,
                    headers=GET_EXPECTED_HEADERS,
                )
            ],
            BrowserRequest.call_args_list,
        )
        BrowserRequest.reset_mock()

        self.assertEqual(HTMLAsset.objects.count(), 1)
        asset = HTMLAsset.objects.get()
        self.assertEqual(asset.url, "http://127.0.0.1/to_cache.png")
        self.assertEqual(asset.filename, "http,3A/127.0.0.1/to_cache.png_55505ba281.png")
        self.assertEqual(asset.url, "http://127.0.0.1/to_cache.png")
        return asset

    def _download_hit(self, BrowserRequest):
        with self.assertRaises(CacheHit) as cm:
            HTMLCache.download(
                "http://127.0.0.1/to_cache.png",
                self.collection,
                "http://127.0.0.1/",
                settings.SOSSE_MAX_HTML_ASSET_SIZE,
            )

        self.assertTrue(BrowserRequest.call_args_list == [], BrowserRequest.call_args_list)
        BrowserRequest.reset_mock()
        return cm.exception.asset

    def _download_not_modified(self, BrowserRequest, modified_since):
        with self.assertRaises(CacheHit) as cm:
            HTMLCache.download(
                "http://127.0.0.1/to_cache.png",
                self.collection,
                "http://127.0.0.1/",
                settings.SOSSE_MAX_HTML_ASSET_SIZE,
            )

        self.assertTrue(
            BrowserRequest.call_args_list
            == [
                mock.call(
                    "http://127.0.0.1/to_cache.png",
                    self.collection,
                    check_status=True,
                    max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE,
                    headers=GET_EXPECTED_HEADERS | {"If-Modified-Since": modified_since},
                )
            ],
            BrowserRequest.call_args_list,
        )
        BrowserRequest.reset_mock()
        return cm.exception.asset

    def _download_refresh(self, BrowserRequest, headers):
        page = HTMLCache.download(
            "http://127.0.0.1/to_cache.png", self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE
        )
        self.assertTrue(isinstance(page, Page))
        headers.update(GET_EXPECTED_HEADERS)
        self.assertTrue(
            BrowserRequest.call_args_list
            == [
                mock.call(
                    "http://127.0.0.1/to_cache.png",
                    self.collection,
                    check_status=True,
                    max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE,
                    headers=headers,
                )
            ],
            BrowserRequest.call_args_list,
        )
        BrowserRequest.reset_mock()
        return page

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    def test_030_heuristic_hit(self, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        last_year = now - timedelta(days=365)
        last_year = last_year.replace(microsecond=0)
        last_year_http = http_date_format(last_year)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {"Date": now_http, "Last-Modified": last_year_http},
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, last_year)
        self.assertIsNone(asset.max_age)
        self.assertIsNone(asset.etag)
        self.assertFalse(asset.has_cache_control)

        _asset = self._download_hit(BrowserRequest)
        self.assertEqual(asset, _asset)
        self.assertTrue(
            _heuristic_check.call_args_list == [mock.call(asset)],
            _heuristic_check.call_args_list,
        )

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    def test_040_heuristic_miss(self, _heuristic_check, BrowserRequest):
        yesterday = timezone.now() - timedelta(days=1)
        yesterday = yesterday.replace(microsecond=0)
        yesterday_http = http_date_format(yesterday)
        previous = yesterday - timedelta(minutes=1)
        previous_http = http_date_format(previous)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {"Date": yesterday_http, "Last-Modified": previous_http},
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertEqual(asset.download_date, yesterday)
        self.assertEqual(asset.last_modified, previous)
        self.assertIsNone(asset.max_age)
        self.assertIsNone(asset.etag)
        self.assertFalse(asset.has_cache_control)

        _asset = self._download_miss(BrowserRequest)
        self.assertEqual(asset, _asset)
        self.assertTrue(
            _heuristic_check.call_args_list == [mock.call(asset)],
            _heuristic_check.call_args_list,
        )

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    @mock.patch("se.html_cache.HTMLCache._max_age_check", wraps=HTMLCache._max_age_check)
    def test_050_expires_hit(self, _max_age_check, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {
                        "Date": now_http,
                        "Last-Modified": http_date_format(now - timedelta(seconds=1)),
                        "Expires": http_date_format(now + timedelta(seconds=59)),
                    },
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_max_age_check.call_args_list == [], _max_age_check.call_args_list)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, now - timedelta(seconds=1))
        self.assertEqual(asset.max_age, 60)
        self.assertIsNone(asset.etag)
        self.assertFalse(asset.has_cache_control)

        _asset = self._download_hit(BrowserRequest)
        self.assertEqual(asset, _asset)
        self.assertTrue(
            _max_age_check.call_args_list
            == [mock.call(asset, self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE)],
            _max_age_check.call_args_list,
        )
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    @mock.patch("se.html_cache.HTMLCache._max_age_check", wraps=HTMLCache._max_age_check)
    def test_060_expires_miss(self, _max_age_check, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {
                        "Date": now_http,
                        "Last-Modified": http_date_format(now - timedelta(seconds=61)),
                        "Expires": http_date_format(now - timedelta(seconds=1)),
                    },
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertTrue(_max_age_check.call_args_list == [], _max_age_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, now - timedelta(seconds=61))
        self.assertEqual(asset.max_age, 60)
        self.assertIsNone(asset.etag)
        self.assertFalse(asset.has_cache_control)

        _asset = self._download_miss(BrowserRequest)
        self.assertEqual(asset, _asset)
        self.assertTrue(
            _max_age_check.call_args_list
            == [mock.call(asset, self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE)],
            _max_age_check.call_args_list,
        )
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    @mock.patch("se.html_cache.HTMLCache._max_age_check", wraps=HTMLCache._max_age_check)
    def test_070_max_age_hit(self, _max_age_check, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "1",
                    },
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_max_age_check.call_args_list == [], _max_age_check.call_args_list)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, now - timedelta(seconds=1))
        self.assertEqual(asset.max_age, 60)
        self.assertIsNone(asset.etag)
        self.assertTrue(asset.has_cache_control)

        _asset = self._download_hit(BrowserRequest)
        self.assertEqual(asset, _asset)
        self.assertTrue(
            _max_age_check.call_args_list
            == [mock.call(asset, self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE)],
            _max_age_check.call_args_list,
        )
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    @mock.patch("se.html_cache.HTMLCache._max_age_check", wraps=HTMLCache._max_age_check)
    def test_080_max_age_not_modified(self, _max_age_check, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "61",
                    },
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertTrue(_max_age_check.call_args_list == [], _max_age_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, now - timedelta(seconds=61))
        self.assertEqual(asset.max_age, 60)
        self.assertIsNone(asset.etag)
        self.assertTrue(asset.has_cache_control)

        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "62",
                    },
                    304,
                )
            }
        )
        _asset = self._download_not_modified(BrowserRequest, now_http)
        self.assertEqual(asset, _asset)
        self.assertTrue(
            _max_age_check.call_args_list
            == [mock.call(asset, self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE)],
            _max_age_check.call_args_list,
        )
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        content = open(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename, "rb").read()
        self.assertEqual(content, b"PNG")

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    @mock.patch("se.html_cache.HTMLCache._max_age_check", wraps=HTMLCache._max_age_check)
    def test_090_max_age_modified(self, _max_age_check, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "61",
                    },
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertTrue(_max_age_check.call_args_list == [], _max_age_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, now - timedelta(seconds=61))
        self.assertEqual(asset.max_age, 60)
        self.assertIsNone(asset.etag)
        self.assertTrue(asset.has_cache_control)

        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG2",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "2",
                    },
                )
            }
        )
        page = self._download_refresh(BrowserRequest, {"If-Modified-Since": now_http})
        self.assertEqual(page.content, b"PNG2")
        self.assertTrue(
            _max_age_check.call_args_list
            == [mock.call(asset, self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE)],
            _max_age_check.call_args_list,
        )
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)

    @mock.patch("se.browser_request.BrowserRequest.get")
    @mock.patch("se.html_cache.HTMLCache._heuristic_check", wraps=HTMLCache._heuristic_check)
    @mock.patch("se.html_cache.HTMLCache._max_age_check", wraps=HTMLCache._max_age_check)
    def test_100_etag_modified(self, _max_age_check, _heuristic_check, BrowserRequest):
        now = timezone.now()
        now = now.replace(microsecond=0)
        now_http = http_date_format(now)
        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "61",
                        "ETag": '"deadbeef"',
                    },
                )
            }
        )

        asset = self._download_miss(BrowserRequest)
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
        self.assertTrue(_max_age_check.call_args_list == [], _max_age_check.call_args_list)
        self.assertEqual(asset.download_date, now)
        self.assertEqual(asset.last_modified, now - timedelta(seconds=61))
        self.assertEqual(asset.max_age, 60)
        self.assertEqual(asset.etag, '"deadbeef"')
        self.assertTrue(asset.has_cache_control)

        BrowserRequest.side_effect = BrowserMock(
            {
                "http://127.0.0.1/to_cache.png": (
                    b"PNG2",
                    {
                        "Date": now_http,
                        "Cache-Control": "max-age=60",
                        "Age": "2",
                    },
                )
            }
        )
        expected_headers = {
            "If-Modified-Since": now_http,
            "If-None-Match": '"deadbeef"',
        }
        page = self._download_refresh(BrowserRequest, expected_headers)
        self.assertEqual(page.content, b"PNG2")
        self.assertTrue(
            _max_age_check.call_args_list
            == [mock.call(asset, self.collection, "http://127.0.0.1/", settings.SOSSE_MAX_HTML_ASSET_SIZE)],
            _max_age_check.call_args_list,
        )
        self.assertTrue(_heuristic_check.call_args_list == [], _heuristic_check.call_args_list)
