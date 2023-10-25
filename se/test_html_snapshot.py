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

from unittest import mock

import cssutils
from django.conf import settings
from django.shortcuts import reverse
from django.test import TransactionTestCase, override_settings
from django.utils.html import format_html
from requests import HTTPError

from .browser import Page
from .document import Document
from .html_asset import HTMLAsset
from .html_cache import HTML_SNAPSHOT_HASH_LEN, max_filename_size
from .html_snapshot import css_parser, extract_css_url, HTMLSnapshot
from .models import CrawlPolicy, DomainSetting
from .test_mock import BrowserMock


class HTMLSnapshotTest:
    def setUp(self):
        self.policy = CrawlPolicy.create_default()
        self.policy.default_browse_mode = DomainSetting.BROWSE_REQUESTS
        self.policy.create_thumbnails = False
        self.policy.save()

    def test_010_html_dump(self):
        HTML = b'<html><head></head><body>test</body></html>'
        page = Page('http://127.0.0.1/', HTML, None)
        dump = page.dump_html()
        self.assertEqual(dump, HTML)

    def test_020_sanitize_tags(self):
        HTML = b'''<html><head>
            <script src="http://127.0.0.1/test.js"></script><link href="test.js" rel="preload"/>
        </head><body>
            test
            <script>console.log('test');</script>
        </body></html>'''

        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).sanitize()
        dump = page.dump_html()
        self.assertEqual(dump, b'<html><head>\n            \n        </head><body>\n            test\n            \n        </body></html>')

    def test_030_remove_favicon(self):
        HTML = b'''<html><head>
            <link rel="icon" src="http://127.0.0.1/test.png"></link>
        </head><body>test</body></html>'''

        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).sanitize()
        dump = page.dump_html()
        self.assertEqual(dump, b'<html><head>\n            \n        </head><body>test</body></html>')

    def test_040_sanitize_attributes(self):
        HTML = b'''<html><head></head><body>
            <div data-test="other" onclick="console.log('test')"></div>
        </body></html>'''

        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).sanitize()
        dump = page.dump_html()
        self.assertEqual(dump, b'''<html><head></head><body>
            <div data-test="other"></div>
        </body></html>''')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_asset.open')
    @mock.patch('se.html_cache.open')
    def test_050_assets_handling(self, cache_open, asset_open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None
        cache_open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        asset_open.side_effect = cache_open.side_effect

        HTML = b'''<html><head>
            <link rel="stylesheet" href="/style.css"/>
        </head><body>
            <img src="/image.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/style.css', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(cache_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/style.css_72f0eee2c7.css', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
        ], cache_open.call_args_list)

        dump = page.dump_html()
        OUTPUT = f'''<html><head>
            <link href="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/style.css_72f0eee2c7.css" rel="stylesheet"/>
        </head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/image.png_62d75f74b8.png"/>
        </body></html>'''.encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(),
                         set(('http://127.0.0.1/style.css', 'http://127.0.0.1/image.png')))
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT),
                         set(('http,3A/127.0.0.1/style.css_72f0eee2c7.css', 'http,3A/127.0.0.1/image.png_62d75f74b8.png')))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_060_srcset_attributes(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)

        HTML = b'''<html><head></head><body>
            <img srcset="image.png 200px, image2.png 300px" src="image3.png"/>
            <video>
                <source srcset="video.mp4"/>
            </video>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image2.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image3.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/video.mp4', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image2.png_d22a588d3b.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image3.png_c2e85796e4.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/video.mp4_60fce7cf30.mp4', 'wb')
        ], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = f'''<html><head></head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/image3.png_c2e85796e4.png" srcset="{settings.SOSSE_HTML_SNAPSHOT_URL}http%2C3A/127.0.0.1/image.png_62d75f74b8.png 200px, {settings.SOSSE_HTML_SNAPSHOT_URL}http%2C3A/127.0.0.1/image2.png_d22a588d3b.png 300px"/>
            <video>
                <source srcset="{settings.SOSSE_HTML_SNAPSHOT_URL}http%2C3A/127.0.0.1/video.mp4_60fce7cf30.mp4"/>
            </video>
        </body></html>'''.encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(),
                         set(('http://127.0.0.1/image.png',
                              'http://127.0.0.1/image2.png',
                              'http://127.0.0.1/image3.png',
                              'http://127.0.0.1/video.mp4')))
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT),
                         set(('http,3A/127.0.0.1/image.png_62d75f74b8.png',
                              'http,3A/127.0.0.1/image2.png_d22a588d3b.png',
                              'http,3A/127.0.0.1/image3.png_c2e85796e4.png',
                              'http,3A/127.0.0.1/video.mp4_60fce7cf30.mp4')))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_070_links_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = b'''<html><head></head><body>
            <a href="http://127.0.0.2/">link</a>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [], RequestBrowser.call_args_list)

        dump = page.dump_html()
        OUTPUT = b'''<html><head></head><body>
            <a href="/html/http://127.0.0.2/">link</a>
        </body></html>'''
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set())
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT), set())

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_080_data_assets(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = b'''<html><head></head><body>
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [], RequestBrowser.call_args_list)

        dump = page.dump_html()
        OUTPUT = b'''<html><head></head><body>
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="/>
        </body></html>'''
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set())
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT), set())

    def test_090_css_parser(self):
        SRC = 'body {src: local(police), url(police.svg) format("svg"), url(police.woff) format("woff")}'
        DST = '''body {
    src: local(police), url(police.svg) format("svg"), url(police.woff) format("woff")
    }'''
        self.assertEqual(cssutils.parseString(SRC).cssText.decode('utf-8'), DST)

        self.assertEqual(cssutils.parseStyle('color: #fff').cssText, 'color: #fff')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_100_css_directives(self, _open, makedirs, RequestBrowser):
        for url_in_css, url_dl, filename in ((b'url("police.woff")', 'police.woff', 'police.woff_644bf7897f.woff'),
                                             (b"url('police.woff')", 'police.woff', 'police.woff_644bf7897f.woff'),
                                             (b"url(  'police.woff'   )", 'police.woff', 'police.woff_644bf7897f.woff'),
                                             (b"url(polic\\ e.woff)", 'polic%20e.woff', 'polic,20e.woff_644bf7897f.woff'),
                                             (b"url('po\"lice.woff')", 'po%22lice.woff', 'po,22lice.woff_644bf7897f.woff'),
                                             (b'url(police.woff)', 'police.woff', 'police.woff_644bf7897f.woff'),):
            RequestBrowser.side_effect = BrowserMock({
                'http://127.0.0.1/po%22lice.woff': b'WOFF test',
                'http://127.0.0.1/polic%20e.woff': b'WOFF test',
            })
            _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
            makedirs.side_effect = None

            CSS = b'''@font-face {
    font-family: "police";
    src: %s
    }''' % url_in_css
            page = Page('http://127.0.0.1/', CSS, None)
            snap = HTMLSnapshot(page, self.policy)
            output = css_parser().handle_css(snap, 'http://127.0.0.1/', CSS, False)

            self.assertTrue(RequestBrowser.call_args_list == [
                mock.call('http://127.0.0.1/' + url_dl, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
            ], RequestBrowser.call_args_list)

            self.assertTrue(_open.call_args_list == [
                mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/' + filename, 'wb')
            ], _open.call_args_list)

            self.assertEqual(output, '''@font-face {
    font-family: "police";
    src: url("%shttp,3A/127.0.0.1/%s")
    }''' % (settings.SOSSE_HTML_SNAPSHOT_URL, filename))

            self.assertEqual(snap.get_asset_urls(), set(('http://127.0.0.1/' + url_dl,)))
            self.assertEqual(css_parser().css_extract_assets(output, False), set(('http,3A/127.0.0.1/' + filename,)))

            _open.reset_mock()
            makedirs.reset_mock()
            RequestBrowser.reset_mock()

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_110_css_content_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = b'''<html><head><style>body {
    src: local(police), url("police.svg") format("svg"), url("police.woff") format("woff")
    }</style></head><body>
            test
            <div style="color: #fff"></div>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/police.svg', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/police.woff', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})

        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/police.svg_614a9bdfc7.svg', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/police.woff_644bf7897f.woff', 'wb')
        ], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = '''<html><head><style>body {
    src: local(police), url("%shttp,3A/127.0.0.1/police.svg_614a9bdfc7.svg") format("svg"), url("%shttp,3A/127.0.0.1/police.woff_644bf7897f.woff") format("woff")
    }</style></head><body>
            test
            <div style="color: #fff"></div>
        </body></html>''' % (settings.SOSSE_HTML_SNAPSHOT_URL, settings.SOSSE_HTML_SNAPSHOT_URL)
        self.assertEqual(dump.decode('utf-8'), OUTPUT)

        self.assertEqual(snap.get_asset_urls(),
                         set(('http://127.0.0.1/police.svg',
                              'http://127.0.0.1/police.woff')))
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT),
                         set(('http,3A/127.0.0.1/police.woff_644bf7897f.woff',
                              'http,3A/127.0.0.1/police.svg_614a9bdfc7.svg')))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_120_css_inline_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = b'''<html><head></head></html>
            <div style='background-image: url("/image.png")'></div>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),

        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
        ], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = '''<html><head></head><body>
            <div style='background-image: url("%shttp,3A/127.0.0.1/image.png_62d75f74b8.png")'></div>
        </body></html>''' % settings.SOSSE_HTML_SNAPSHOT_URL
        self.assertEqual(dump.decode('utf-8'), OUTPUT)

        self.assertEqual(snap.get_asset_urls(),
                         set(('http://127.0.0.1/image.png',)))
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT),
                         set(('http,3A/127.0.0.1/image.png_62d75f74b8.png',)))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_130_css_data_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = b'''<html><head><style>body {
    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==")
    }</style></head><body>
            test
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [], _open.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, HTML)

        self.assertEqual(snap.get_asset_urls(), set())
        self.assertEqual(HTMLAsset.html_extract_assets(HTML), set())

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_140_html_asset(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = b'''<html><head></head><body>
            <img src="/page.html"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/page.html', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = b'''<html><head></head><body>
            <img src="/html/http://127.0.0.1/page.html"/>
        </body></html>'''
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set())
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT), set())

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    def test_150_page_too_big(self, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None

        HTML = b'''<html><head></head><body>
            <img src="/toobig.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)

        mock_open = mock.mock_open()
        with mock.patch('se.html_cache.open', mock_open):
            snap = HTMLSnapshot(page, self.policy)
            snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/toobig.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(mock_open.mock_calls == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/toobig.png_89ad261c12.txt', 'wb'),
            mock.call().__enter__(),
            mock.call().write(b'An error occured while downloading http://127.0.0.1/toobig.png:\nDocument size is too big (2.0kB > 1.0kB). You can increase the `max_file_size` and `max_html_asset_size` option in the configuration to index this file.'),
            mock.call().__exit__(None, None, None)
        ], mock_open.mock_calls)

        dump = page.dump_html()
        OUTPUT = f'''<html><head></head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/toobig.png_89ad261c12.txt"/>
        </body></html>'''.encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set(('http://127.0.0.1/toobig.png',)))
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT), set(('http,3A/127.0.0.1/toobig.png_89ad261c12.txt',)))

    @override_settings(TEST_MODE=False)
    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    def test_160_exception_handling(self, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None

        HTML = b'''<html><head></head><body>
            <img src="/exception.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)

        mock_open = mock.mock_open()
        with mock.patch('se.html_cache.open', mock_open):
            snap = HTMLSnapshot(page, self.policy)
            snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/exception.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertRegex(mock_open.mock_calls[0].args[0], '^' + settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/exception.png_[^.]+.txt')
        self.assertIn(b'Traceback (most recent call last):', mock_open.mock_calls[2].args[0])
        self.assertIn(b'Exception: Generic exception', mock_open.mock_calls[2].args[0])

        urls = snap.get_asset_urls()
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls.pop(), 'http://127.0.0.1/exception.png')

        filenames = HTMLAsset.html_extract_assets(page.dump_html())
        self.assertEqual(len(filenames), 1)
        self.assertRegex(filenames.pop(), 'http,3A/127.0.0.1/exception.png_[^.]+.txt')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_170_max_filename(self, _open, makedirs, RequestBrowser):
        makedirs.side_effect = None
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        CONTENT = b'content'
        HASH = '9a0364b9e9'

        web = {}
        d = HTML_SNAPSHOT_HASH_LEN + len('http://127.0.0.1/' + '.html') + 10
        for i in range(max_filename_size() - d, max_filename_size() + d):
            long_filename = ('a' * i) + '.png'
            long_file_url = 'http://127.0.0.1/' + long_filename
            web[long_file_url] = CONTENT

            long_dirname = 'a' * i
            long_dir_url = 'http://127.0.0.1/' + long_dirname + '/test.png'
            web[long_dir_url] = CONTENT

            RequestBrowser.side_effect = BrowserMock(web)
            HTML = b'''<html><head></head><body>
                <img src="%s"/>
                <img src="%s"/>
            </body></html>''' % (long_file_url.encode('utf-8'), long_dir_url.encode('utf-8'))
            page = Page('http://127.0.0.1/', HTML, None)
            snap = HTMLSnapshot(page, self.policy)
            snap.handle_assets()

            self.assertTrue(RequestBrowser.call_args_list == [
                mock.call(long_file_url, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
                mock.call(long_dir_url, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
            ], RequestBrowser.call_args_list)

            long_url_filename = _open.call_args_list[0].args[0].split('/')[-1]
            self.assertTrue(len(long_url_filename) <= max_filename_size())
            if f'{long_filename}_{HASH}.png' != long_url_filename:
                self.assertEqual(len(long_url_filename), max_filename_size())
                prefix, suffix = long_url_filename.split('_', 1)
                self.assertTrue(long_url_filename.startswith(prefix))
                self.assertEqual(suffix, f'{HASH}.png')

            long_url_dirname = _open.call_args_list[1].args[0].split('/')[-2]
            self.assertTrue(len(long_url_dirname) <= max_filename_size())
            if long_dirname != long_url_dirname:
                dn = long_dirname[:max_filename_size() - len(HASH) - 1]
                dn += '_' + HASH
                self.assertEqual(long_url_dirname, dn)

            assets = set([a.args[0][len(settings.SOSSE_HTML_SNAPSHOT_DIR):] for a in _open.call_args_list])
            self.assertEqual(snap.get_asset_urls(), set((long_file_url, long_dir_url)))
            self.assertEqual(HTMLAsset.html_extract_assets(page.dump_html()), assets)

            RequestBrowser.reset_mock()
            _open.reset_mock()

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_180_exclude_url(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        policy = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/.*', snapshot_exclude_url_re='http://127.0.0.1/excluded.*')
        HTML = b'''<html><head></head><body>
            <img src="/excluded.png"/>
            <img src="/image.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
        ], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = format_html('''<html><head></head><body>
            <img src="{}"/>
            <img src="{}http,3A/127.0.0.1/image.png_62d75f74b8.png"/>
        </body></html>''', reverse('html_excluded', args=(policy.id, 'url',)), settings.SOSSE_HTML_SNAPSHOT_URL).encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set(('http://127.0.0.1/image.png',)))
        self.assertEqual(HTMLAsset.html_extract_assets(page.dump_html()), set(('http,3A/127.0.0.1/image.png_62d75f74b8.png',)))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_190_exclude_mime(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        policy = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/.*', snapshot_exclude_mime_re='image/jpe?g')
        HTML = b'''<html><head></head><body>
            <img src="/image.jpg"/>
            <img src="/image.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.jpg', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
        ], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = format_html('''<html><head></head><body>
            <img src="{}"/>
            <img src="{}http,3A/127.0.0.1/image.png_62d75f74b8.png"/>
        </body></html>''', reverse('html_excluded', args=(policy.id, 'mime',)), settings.SOSSE_HTML_SNAPSHOT_URL).encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set(('http://127.0.0.1/image.png',)))
        self.assertEqual(HTMLAsset.html_extract_assets(page.dump_html()), set(('http,3A/127.0.0.1/image.png_62d75f74b8.png',)))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def test_200_exclude_element(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        policy = CrawlPolicy.objects.create(url_regex='http://127.0.0.1/.*', snapshot_exclude_element_re='aud.*')
        HTML = b'''<html><head></head><body>
            <audio src="/audio.wav"></audio>
            <video src="/video.mp4"></video>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, policy)
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/video.mp4', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
        ], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/video.mp4_60fce7cf30.mp4', 'wb'),
        ], _open.call_args_list)

        dump = page.dump_html()
        OUTPUT = format_html('''<html><head></head><body>
            <audio src="{}"></audio>
            <video src="{}http,3A/127.0.0.1/video.mp4_60fce7cf30.mp4"></video>
        </body></html>''', reverse('html_excluded', args=(policy.id, 'element',)), settings.SOSSE_HTML_SNAPSHOT_URL).encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(), set(('http://127.0.0.1/video.mp4',)))
        self.assertEqual(HTMLAsset.html_extract_assets(page.dump_html()), set(('http,3A/127.0.0.1/video.mp4_60fce7cf30.mp4',)))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_cache.open')
    def _snapshot_page(self, url, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        HTML = b'''<html><head></head><body>
            <img src="/image.png"/>
            <img src="/image.png"/>
        </body></html>'''

        page = Page('http://127.0.0.1/' + url, HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.snapshot()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/%s_81faf90c0b.html' % url, 'wb'),
        ], _open.call_args_list)

    def test_210_asset_add_ref(self):
        assets = HTMLAsset.objects.all()
        self.assertEqual(len(assets), 0)

        self._snapshot_page('page1.html')
        assets = HTMLAsset.objects.order_by('download_date')
        self.assertEqual(len(assets), 2)
        asset_png = assets.first()
        self.assertEqual(asset_png.url, 'http://127.0.0.1/image.png')
        self.assertEqual(asset_png.filename, 'http,3A/127.0.0.1/image.png_62d75f74b8.png')
        self.assertEqual(asset_png.ref_count, 1)
        asset_html1 = assets.last()
        self.assertEqual(asset_html1.url, 'http://127.0.0.1/page1.html')
        self.assertEqual(asset_html1.filename, 'http,3A/127.0.0.1/page1.html_81faf90c0b.html')
        self.assertEqual(asset_html1.ref_count, 1)

        self._snapshot_page('page2.html')
        assets = HTMLAsset.objects.order_by('download_date')
        self.assertEqual(len(assets), 3)
        self.assertEqual(assets[0], asset_html1)
        asset_html1.refresh_from_db()
        self.assertEqual(asset_html1.ref_count, 1)

        self.assertEqual(assets[1], asset_png)
        asset_png.refresh_from_db()
        self.assertEqual(asset_png.ref_count, 2)

        asset_html2 = assets.last()
        self.assertEqual(asset_html2.url, 'http://127.0.0.1/page2.html')
        self.assertEqual(asset_html2.filename, 'http,3A/127.0.0.1/page2.html_81faf90c0b.html')
        self.assertEqual(asset_html2.ref_count, 1)

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('os.unlink')
    @mock.patch('os.rmdir')
    def test_220_asset_remove(self, rmdir, unlink, makedirs, RequestBrowser):
        HTML = b'''<html><head></head><body>
            <img src="%s"/>
        </body></html>'''
        PNG_URL = 'http,3A/127.0.0.1/image.png_62d75f74b8.png'
        RequestBrowser.side_effect = BrowserMock({
            'http://127.0.0.1/page1.html': HTML % b'/image.png',
            'http://127.0.0.1/page2.html': HTML % b'/image.png',
            'http://127.0.0.1/robots.txt': HTTPError(),
            'http://127.0.0.1/favicon.ico': HTTPError(),
        })
        makedirs.side_effect = None

        for no in (1, 2):
            mock_open = mock.mock_open()
            with mock.patch('se.html_asset.open', mock_open), mock.patch('se.html_cache.open', mock_open):
                Document.objects.create(url='http://127.0.0.1/page%s.html' % no)
                Document.crawl(0)
                self.assertEqual(mock_open.mock_calls[0],
                                 mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + PNG_URL, 'wb'))
                self.assertEqual(mock_open.mock_calls[4],
                                 mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/page%i.html_3acae9ed94.html' % no, 'wb'))

        self.assertEqual(HTMLAsset.objects.count(), 3)
        self.assertEqual(HTMLAsset.objects.get(url='http://127.0.0.1/image.png').ref_count, 2)

        png_url_bytes = (settings.SOSSE_HTML_SNAPSHOT_URL + PNG_URL).encode('utf-8')
        mock_open = mock.mock_open(read_data=HTML % png_url_bytes)
        with mock.patch('se.html_asset.open', mock_open), mock.patch('se.html_cache.open', mock_open):
            obj = Document.objects.first()
            obj.delete_html()
            obj.delete()
            self.assertEqual(HTMLAsset.objects.count(), 2)
            self.assertEqual(HTMLAsset.objects.get(url='http://127.0.0.1/image.png').ref_count, 1)
            self.assertTrue(unlink.call_args_list == [
                mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/page1.html_3acae9ed94.html')
            ], unlink.call_args_list)
            unlink.reset_mock()

            obj = Document.objects.first()
            obj.delete_html()
            obj.delete()
            self.assertEqual(HTMLAsset.objects.count(), 0)
            self.assertTrue(unlink.call_args_list == [
                mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png'),
                mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/page2.html_3acae9ed94.html'),
            ], unlink.call_args_list)

    @mock.patch('se.html_asset.remove_html_asset_file')
    def test_230_asset_duplicate_fn(self, remove_html_asset_file):
        self.assertEqual(HTMLAsset.objects.count(), 0)
        asset1 = HTMLAsset.objects.create(url='url1', filename='filename')
        asset1.init_ref_count()
        asset1.refresh_from_db()
        self.assertEqual(asset1.ref_count, 0)
        asset1.increment_ref()
        asset1.refresh_from_db()
        self.assertEqual(asset1.ref_count, 1)

        asset2 = HTMLAsset.objects.create(url='url2', filename='filename')
        self.assertEqual(asset2.ref_count, 0)
        asset2.init_ref_count()
        asset2.refresh_from_db()
        self.assertEqual(asset2.ref_count, 1)
        asset2.increment_ref()
        asset2.refresh_from_db()

        asset1.refresh_from_db()
        self.assertEqual(asset1.ref_count, 2)
        self.assertEqual(asset2.ref_count, 2)

        self.assertTrue(remove_html_asset_file.call_args_list == [], remove_html_asset_file.call_args_list)

        HTMLAsset.remove_file_ref('filename')
        self.assertEqual(HTMLAsset.objects.count(), 2)
        self.assertEqual(list(HTMLAsset.objects.values_list('ref_count', flat=True)), [1, 1])
        self.assertTrue(remove_html_asset_file.call_args_list == [], remove_html_asset_file.call_args_list)

        HTMLAsset.remove_file_ref('filename')
        self.assertEqual(HTMLAsset.objects.count(), 0)
        self.assertTrue(remove_html_asset_file.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'filename')
        ], remove_html_asset_file.call_args_list)

    @mock.patch('se.html_asset.remove_html_asset_file')
    def test_240_asset_duplicate_url(self, remove_html_asset_file):
        self.assertEqual(HTMLAsset.objects.count(), 0)
        asset1 = HTMLAsset.objects.create(url='url', filename='filename1')
        asset1.init_ref_count()
        asset1.refresh_from_db()
        self.assertEqual(asset1.ref_count, 0)
        asset1.increment_ref()
        asset1.refresh_from_db()
        self.assertEqual(asset1.ref_count, 1)

        asset2 = HTMLAsset.objects.create(url='url', filename='filename2')
        self.assertEqual(asset2.ref_count, 0)
        asset2.init_ref_count()
        asset2.refresh_from_db()
        self.assertEqual(asset2.ref_count, 0)
        asset2.increment_ref()
        asset2.refresh_from_db()

        asset1.refresh_from_db()
        self.assertEqual(asset1.ref_count, 1)
        self.assertEqual(asset2.ref_count, 1)

        self.assertTrue(remove_html_asset_file.call_args_list == [], remove_html_asset_file.call_args_list)

        HTMLAsset.remove_file_ref('filename1')
        self.assertEqual(HTMLAsset.objects.count(), 1)
        self.assertEqual(list(HTMLAsset.objects.values_list('ref_count', flat=True)), [1])
        self.assertTrue(remove_html_asset_file.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'filename1')
        ], remove_html_asset_file.call_args_list)
        remove_html_asset_file.reset_mock()

        HTMLAsset.remove_file_ref('filename2')
        self.assertEqual(HTMLAsset.objects.count(), 0)
        self.assertTrue(remove_html_asset_file.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'filename2')
        ], remove_html_asset_file.call_args_list)

    @override_settings(TEST_HTML_ERROR_HANDLING=True)
    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('os.unlink')
    @mock.patch('os.rmdir')
    def test_250_html_error_handling(self, rmdir, unlink, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})

        HTML = b'''<html><head></head><body>
            <img src="/image.png"/>
            <img src="/test-exception"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        snap = HTMLSnapshot(page, self.policy)

        mock_open = mock.mock_open()
        with mock.patch('se.html_cache.open', mock_open):
            snap.snapshot()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
        ], RequestBrowser.call_args_list)

        self.assertTrue(unlink.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png'),
        ], unlink.call_args_list)

        self.assertEqual(mock_open.mock_calls[0].args[0], settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png')
        self.assertRegex(mock_open.mock_calls[4].args[0], settings.SOSSE_HTML_SNAPSHOT_DIR + r'http,3A/127\.0\.0\.1/_[^.]+\.html')

        self.assertIn(b'Traceback (most recent call last):', mock_open.mock_calls[6].args[0])
        self.assertIn(b'Exception: html_error_handling test', mock_open.mock_calls[6].args[0])

        self.assertEqual(HTMLAsset.objects.count(), 1)
        asset = HTMLAsset.objects.first()
        self.assertEqual(asset.url, 'http://127.0.0.1/')
        self.assertRegex(asset.filename, r'http,3A/127\.0\.0\.1/_[^.]+\.html')
        self.assertEqual(asset.ref_count, 1)

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_asset.open')
    @mock.patch('se.html_cache.open')
    def test_260_base_header(self, cache_open, asset_open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None
        cache_open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        asset_open.side_effect = cache_open.side_effect

        HTML = b'''<html><head>
            <base href="/"/>
            <link rel="stylesheet" href="style.css"/>
        </head><body>
            <img src="image.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/path/page.html', HTML, None)
        snap = HTMLSnapshot(page, self.policy)
        snap.sanitize()
        snap.handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/style.css', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image.png', check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(cache_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/style.css_72f0eee2c7.css', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_62d75f74b8.png', 'wb'),
        ], cache_open.call_args_list)

        dump = page.dump_html()
        OUTPUT = f'''<html><head>
            \n            <link href="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/style.css_72f0eee2c7.css" rel="stylesheet"/>
        </head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/image.png_62d75f74b8.png"/>
        </body></html>'''.encode('utf-8')
        self.assertEqual(dump, OUTPUT)

        self.assertEqual(snap.get_asset_urls(),
                         set(('http://127.0.0.1/style.css', 'http://127.0.0.1/image.png')))
        self.assertEqual(HTMLAsset.html_extract_assets(OUTPUT),
                         set(('http,3A/127.0.0.1/style.css_72f0eee2c7.css', 'http,3A/127.0.0.1/image.png_62d75f74b8.png')))


class HTMLSnapshotCSSUtilsParser(HTMLSnapshotTest, TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        import se.html_snapshot
        cls.InternalCSSParser = se.html_snapshot.InternalCSSParser
        se.html_snapshot.InternalCSSParser = se.html_snapshot.CSSUtilsParser

    @classmethod
    def tearDownClass(cls):
        import se.html_snapshot
        se.html_snapshot.InternalCSSParser = cls.InternalCSSParser


class HTMLSnapshotInternalCSSParser(HTMLSnapshotTest, TransactionTestCase):
    pass


class CSSUrlExtractor(TransactionTestCase):
    def test_css_url_extract(self):
        CSS = '''@font-url { url('test'); }'''
        PARSED = ((False, '@font-url { '),
                  (True, 'test'),
                  (False, '; }'))

        for no, segment in enumerate(extract_css_url(CSS)):
            self.assertEqual(segment, PARSED[no])

    def test_css_url_extract_no_url(self):
        CSS = '''@font-url { rl('test'); }'''
        PARSED = ((False, "@font-url { rl('test'); }"),)
        for no, segment in enumerate(extract_css_url(CSS)):
            self.assertEqual(segment, PARSED[no])

    def test_css_url_extract_quote(self):
        CSS = '''@font-url { url('te"st'); }'''
        PARSED = ((False, '@font-url { '),
                  (True, 'te"st'),
                  (False, '; }'))

        for no, segment in enumerate(extract_css_url(CSS)):
            self.assertEqual(segment, PARSED[no])

    def test_css_url_extract_non_url(self):
        CSS = '''@font-url { url('data:image/png;base64,iV'); }'''
        PARSED = ((False, '@font-url { '),
                  (False, "url('data:image/png;base64,iV')"),
                  (False, '; }'))

        for no, segment in enumerate(extract_css_url(CSS)):
            self.assertEqual(segment, PARSED[no])

    def test_css_url_extract_escape(self):
        CSS = r'''@font-url { url('test\'plop'); }'''
        PARSED = ((False, '@font-url { '),
                  (True, "test'plop"),
                  (False, '; }'))

        for no, segment in enumerate(extract_css_url(CSS)):
            self.assertEqual(segment, PARSED[no])
