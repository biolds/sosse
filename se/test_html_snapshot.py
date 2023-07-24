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

from mimetypes import guess_type
from unittest import mock

import cssutils
from django.conf import settings
from django.test import TestCase, override_settings

from .browser import Page, PageTooBig
from .html_snapshot import HTMLSnapshot, HTML_SNAPSHOT_HASH_LEN, max_filename_size
from .models import CrawlPolicy


class BrowserMock:
    def __init__(self, web):
        self.web = {
            'http://127.0.0.1/style.css': b'body { color: #fff; }',
            'http://127.0.0.1/page.html': b'HTML test',
            'http://127.0.0.1/image.png': b'PNG test',
            'http://127.0.0.1/image2.png': b'PNG test2',
            'http://127.0.0.1/image3.png': b'PNG test3',
            'http://127.0.0.1/video.mp4': b'MP4 test',
            'http://127.0.0.1/police.svg': b'SVG test',
            'http://127.0.0.1/police.woff': b'WOFF test',
            'http://127.0.0.1/toobig.png': PageTooBig(2000, 1),
            'http://127.0.0.1/exception.png': Exception('Generic exception')
        }
        self.web.update(web)

    def __call__(self, url, raw=False, check_status=False, **kwargs):
        content = self.web[url]
        if isinstance(content, Exception):
            raise content
        mimetype = guess_type(url)[0]
        return Page(url, content, BrowserMock, mimetype)


class HtmlSnapshotTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = CrawlPolicy.create_default()

    @classmethod
    def tearDownClass(cls):
        cls.policy.delete()

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

    def test_050_html_filenames(self):
        for url, fn in (
            ('http://127.0.0.1/test.html', 'http,3A/127.0.0.1/test.html_~~~.html'),
            ('http://127.0.0.1/test.html?a=b', 'http,3A/127.0.0.1/test.html,3Fa,3Db_~~~.html'),
            ('http://127.0.0.1/', 'http,3A/127.0.0.1/_~~~.html'),
            ('http://127.0.0.1/../', 'http,3A/127.0.0.1/_~~~.html'),
            ('http://127.0.0.1/,', 'http,3A/127.0.0.1/,2C_~~~.html'),
        ):
            _fn = HTMLSnapshot.html_filename(url, '~~~', '.html')
            self.assertEqual(_fn, fn, f'failed on {url} / expected {fn} / got {_fn}')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_060_assets_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)

        HTML = '''<html><head>
            <link rel="stylesheet" href="/style.css"/>
        </head><body>
            <img src="/image.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/style.css', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image.png', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/style.css_72f0eee2c7.css', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_0fcab19ae8.png', 'wb'),
        ], _open.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, f'''<html><head>
            <link href="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/style.css_72f0eee2c7.css" rel="stylesheet"/>
        </head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/image.png_0fcab19ae8.png"/>
        </body></html>'''.encode('utf-8'))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_070_srcset_attributes(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)

        HTML = '''<html><head></head><body>
            <img srcset="image.png 200px, image2.png 300px" src="image3.png"/>
            <video>
                <source srcset="video.mp4"/>
            </video>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/image.png', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image2.png', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/image3.png', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/video.mp4', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image.png_0fcab19ae8.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image2.png_d22a588d3b.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/image3.png_c2e85796e4.png', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/video.mp4_60fce7cf30.mp4', 'wb')
        ], _open.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, f'''<html><head></head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/image3.png_c2e85796e4.png" srcset="{settings.SOSSE_HTML_SNAPSHOT_URL}http%2C3A/127.0.0.1/image.png_0fcab19ae8.png 200px, {settings.SOSSE_HTML_SNAPSHOT_URL}http%2C3A/127.0.0.1/image2.png_d22a588d3b.png 300px"/>
            <video>
                <source srcset="{settings.SOSSE_HTML_SNAPSHOT_URL}http%2C3A/127.0.0.1/video.mp4_60fce7cf30.mp4"/>
            </video>
        </body></html>'''.encode('utf-8'))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_080_links_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = '''<html><head></head><body>
            <a href="http://127.0.0.2/">link</a>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [], RequestBrowser.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, b'''<html><head></head><body>
            <a href="/html/http://127.0.0.2/">link</a>
        </body></html>''')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_090_data_assets(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = '''<html><head></head><body>
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [], RequestBrowser.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, b'''<html><head></head><body>
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="/>
        </body></html>''')

    def test_100_css_parser(self):
        SRC = 'body {src: local(police), url(police.svg) format("svg"), url(police.woff) format("woff")}'
        DST = '''body {
    src: local(police), url(police.svg) format("svg"), url(police.woff) format("woff")
    }'''
        self.assertEqual(cssutils.parseString(SRC).cssText.decode('utf-8'), DST)

        self.assertEqual(cssutils.parseStyle('color: #fff').cssText, 'color: #fff')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_110_css_directives(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        CSS = '''@font-face {
    font-family: "police";
    src: url(police.woff);
}'''
        page = Page('http://127.0.0.1/', CSS, None)
        output = HTMLSnapshot(page, self.policy).handle_css('http://127.0.0.1/', CSS, False)

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/police.woff', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})

        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/police.woff_644bf7897f.woff', 'wb')
        ], _open.call_args_list)

        self.assertEqual(output, '''@font-face {
    font-family: "police";
    src: url("%shttp,3A/127.0.0.1/police.woff_644bf7897f.woff")
    }''' % settings.SOSSE_HTML_SNAPSHOT_URL)

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_120_css_content_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = '''<html><head><style>body {src: local(police), url(police.svg) format("svg"), url(police.woff) format("woff")}</style></head><body>
            test
            <div style="color: #fff"></div>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/police.svg', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
            mock.call('http://127.0.0.1/police.woff', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})

        ], RequestBrowser.call_args_list)

        self.assertTrue(_open.call_args_list == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/police.svg_614a9bdfc7.svg', 'wb'),
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/police.woff_644bf7897f.woff', 'wb')
        ], _open.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump.decode('utf-8'), '''<html><head><style>body {
    src: local(police), url("%shttp,3A/127.0.0.1/police.svg_614a9bdfc7.svg") format("svg"), url("%shttp,3A/127.0.0.1/police.woff_644bf7897f.woff") format("woff")
    }</style></head><body>
            test
            <div style="color: #fff"></div>
        </body></html>''' % (settings.SOSSE_HTML_SNAPSHOT_URL, settings.SOSSE_HTML_SNAPSHOT_URL))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_130_css_data_handling(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = '''<html><head><style>body {
    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==")
    }</style></head><body>
            test
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [], _open.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, HTML.encode('utf-8'))

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
    def test_140_html_asset(self, _open, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        _open.side_effect = lambda *args, **kwargs: open('/dev/null', *args[1:], **kwargs)
        makedirs.side_effect = None

        HTML = '''<html><head></head><body>
            <img src="/page.html"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)
        HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/page.html', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)
        self.assertTrue(_open.call_args_list == [], _open.call_args_list)

        dump = page.dump_html()
        self.assertEqual(dump, b'''<html><head></head><body>
            <img src="/html/http://127.0.0.1/page.html"/>
        </body></html>''')

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    def test_150_page_too_big(self, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None

        HTML = '''<html><head></head><body>
            <img src="/toobig.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)

        mock_open = mock.mock_open()
        with mock.patch('se.html_snapshot.open', mock_open):
            HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/toobig.png', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertTrue(mock_open.mock_calls == [
            mock.call(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/toobig.png_89ad261c12.txt', 'wb'),
            mock.call().__enter__(),
            mock.call().write(b'An error occured while downloading http://127.0.0.1/toobig.png:\nDocument size is too big (2.0kB > 1.0kB). You can increase the `max_file_size` and `max_html_asset_size` option in the configuration to index this file.'),
            mock.call().__exit__(None, None, None)
        ], mock_open.mock_calls)

        dump = page.dump_html()
        self.assertEqual(dump, f'''<html><head></head><body>
            <img src="{settings.SOSSE_HTML_SNAPSHOT_URL}http,3A/127.0.0.1/toobig.png_89ad261c12.txt"/>
        </body></html>'''.encode('utf-8'))

    @override_settings(TEST_MODE=False)
    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    def test_160_exception_handling(self, makedirs, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({})
        makedirs.side_effect = None

        HTML = '''<html><head></head><body>
            <img src="/exception.png"/>
        </body></html>'''
        page = Page('http://127.0.0.1/', HTML, None)

        mock_open = mock.mock_open()
        with mock.patch('se.html_snapshot.open', mock_open):
            HTMLSnapshot(page, self.policy).handle_assets()

        self.assertTrue(RequestBrowser.call_args_list == [
            mock.call('http://127.0.0.1/exception.png', raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
        ], RequestBrowser.call_args_list)

        self.assertRegex(mock_open.mock_calls[0].args[0], '^' + settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1/exception.png_[^.]+.txt')
        self.assertIn(b'Traceback (most recent call last):', mock_open.mock_calls[2].args[0])
        self.assertIn(b'Exception: Generic exception', mock_open.mock_calls[2].args[0])

    @mock.patch('se.browser.RequestBrowser.get')
    @mock.patch('os.makedirs')
    @mock.patch('se.html_snapshot.open')
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
            HTML = '''<html><head></head><body>
                <img src="%s"/>
                <img src="%s"/>
            </body></html>''' % (long_file_url, long_dir_url)
            page = Page('http://127.0.0.1/', HTML, None)
            HTMLSnapshot(page, self.policy).handle_assets()

            self.assertTrue(RequestBrowser.call_args_list == [
                mock.call(long_file_url, raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'}),
                mock.call(long_dir_url, raw=True, check_status=True, max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
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

            RequestBrowser.reset_mock()
            _open.reset_mock()
