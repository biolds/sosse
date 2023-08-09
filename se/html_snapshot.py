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

import logging
import re

from traceback import format_exc

from bs4 import NavigableString
import cssutils
from django.conf import settings
from django.shortcuts import reverse
from django.utils.html import format_html

from .browser import SkipIndexing
from .html_cache import HTMLCache, CacheHit
from .utils import has_browsable_scheme


logger = logging.getLogger('html_snapshot')


def css_parser():
    if settings.SOSSE_CSS_PARSER == 'internal':
        return InternalCSSParser
    else:
        return CSSUtilsParser


class InternalCSSParser:
    @staticmethod
    def handle_css(snapshot, src_url, content, inline_css):
        if inline_css:
            assert isinstance(content, str), content.__class__.__name__
        else:
            assert isinstance(content, (bytes, NavigableString)), content.__class__.__name__
            if isinstance(content, bytes):
                content = content.decode('utf-8')
        from .document import absolutize_url
        val = ''

        m = list(re.finditer(r'\burl\([^\)]+\)', content))
        if m:
            for no, css_url in enumerate(m):
                if no == 0:
                    start = 0
                else:
                    start = m[no - 1].end()
                val += content[start:css_url.start()]

                url = css_url[0][4:-1].strip()
                quote = ''
                if url.startswith('"') or url.startswith("'"):
                    quote = url[0]
                    url = url[1:-1]

                if has_browsable_scheme(url):
                    url = absolutize_url(src_url, url, True, True)
                    url = snapshot.download_asset(url)

                url = f'{quote}{url}{quote}'
                val += f'url({url})'

            val += content[m[-1].end(0):]
            css = val
        else:
            css = content
        assert isinstance(css, str)
        return css

    @staticmethod
    def css_extract_assets(content, _):
        assets = set()
        m = list(re.finditer(r'\burl\([^\)]+\)', content))
        if m:
            for css_url in m:
                url = css_url[0][4:-1].strip()
                if url.startswith('"') or url.startswith("'"):
                    url = url[1:-1]

                if url.startswith(settings.SOSSE_HTML_SNAPSHOT_URL):
                    assets.add(url[len(settings.SOSSE_HTML_SNAPSHOT_URL):])

        return assets


class CSSUtilsParser:
    @staticmethod
    def css_declarations(content, inline_css):
        if inline_css:
            declarations = cssutils.parseStyle(content)
            sheet = None
        else:
            sheet = cssutils.parseString(content)
            declarations = []
            for rule in sheet:
                if hasattr(rule, 'style'):
                    declarations += rule.style
        return declarations, sheet

    @staticmethod
    def handle_css(snapshot, src_url, content, inline_css):
        if inline_css:
            assert isinstance(content, str), content.__class__.__name__
        else:
            assert isinstance(content, (bytes, NavigableString)), content.__class__.__name__
        from .document import absolutize_url
        declarations, sheet = CSSUtilsParser.css_declarations(content, inline_css)

        for prop in declarations:
            value = prop.value
            val = ''

            m = list(re.finditer(r'\burl\([^\)]+\)', value))
            if m:
                for no, css_url in enumerate(m):
                    if no == 0:
                        start = 0
                    else:
                        start = m[no - 1].end()
                    val += value[start:css_url.start()]

                    url = css_url[0][4:-1]
                    has_quotes = False
                    if url.startswith('"'):
                        url = url[1:-1]

                    if not url.startswith('data:') and not url.startswith('#'):
                        url = absolutize_url(src_url, url, True, True)
                        url = snapshot.download_asset(url)

                    if has_quotes:
                        url = f'"{url}"'

                    val += f'url({url})'

                val += value[m[-1].end(0):]
                prop.value = val

        if inline_css:
            css = declarations.cssText
        else:
            css = sheet.cssText.decode('utf-8')
        assert isinstance(css, str)
        return css

    @staticmethod
    def css_extract_assets(content, inline_css):
        assets = set()
        declarations, sheet = CSSUtilsParser.css_declarations(content, inline_css)

        for prop in declarations:
            value = prop.value
            m = list(re.finditer(r'\burl\([^\)]+\)', value))
            if m:
                for css_url in m:
                    url = css_url[0][4:-1]
                    if url.startswith('"'):
                        url = url[1:-1]

                    if url.startswith(settings.SOSSE_HTML_SNAPSHOT_URL):
                        assets.add(url[len(settings.SOSSE_HTML_SNAPSHOT_URL):])

        return assets


class HTMLSnapshot:
    def __init__(self, page, crawl_policy):
        self.page = page
        self.crawl_policy = crawl_policy
        self.assets = set()
        self.assets = set()
        self.asset_urls = set()

    def _clear_assets(self):
        for asset in self.assets:
            asset.remove_ref()
        self.assets = set()
        self.asset_urls = set()

    def _add_asset(self, asset):
        self.assets.add(asset)
        self.asset_urls.add(asset.url)

    def snapshot(self):
        logger.debug('snapshot of %s' % self.page.url)
        try:
            self.sanitize()
            self.handle_assets()
            HTMLCache.write_asset(self.page.url, self.page.dump_html(), self.page, extension='.html')
        except Exception as e:  # noqa
            if getattr(settings, 'TEST_MODE', False) and not getattr(settings, 'TEST_HTML_ERROR_HANDLING', False):
                raise
            logger.error('html_snapshot of %s failed:\n%s', self.page.url, format_exc())
            content = 'An error occured while downloading %s:\n%s' % (self.page.url, format_exc())
            content = format_html('<pre>{}</pre>', content)
            content = content.encode('utf-8')
            HTMLCache.write_asset(self.page.url, content, self.page, extension='.html')
            self._clear_assets()

        logger.debug('html_snapshot of %s done' % self.page.url)

    def sanitize(self):
        logger.debug('html_sanitize of %s' % self.page.url)
        soup = self.page.get_soup()

        # Drop <script>
        for elem in soup.find_all('script'):
            elem.extract()

        # Drop event handlers on*
        for elem in soup.find_all(True):
            to_drop = []
            for attr in elem.attrs.keys():
                if attr.startswith('on'):
                    to_drop.append(attr)
            for attr in to_drop:
                elem.attrs.pop(attr)

            if 'nonce' in elem.attrs:
                del elem.attrs['nonce']

        # Drop base elements
        for elem in soup.find_all('base'):
            elem.extract()

        # Drop favicon
        for elem in soup.find_all('link'):
            if elem.attrs.get('itemprop'):
                elem.extract()
                continue

            rel = ' '.join(elem.attrs.get('rel', []))
            for val in ('icon', 'canonical', 'alternate', 'preload'):
                if val in rel:
                    elem.extract()
                    break

    def handle_assets(self):
        logger.debug('html_handle_assets for %s' % self.page.url)
        from .document import absolutize_url

        for elem in self.page.get_soup().find_all(True):
            if elem.name == 'base':
                continue

            if elem.name == 'style':
                logger.debug('handle_css of %s (<style>)' % self.page.url)
                if elem.string:
                    elem.string = css_parser().handle_css(self, self.page.url, elem.string, False)

            if elem.attrs.get('style'):
                logger.debug('handle_css of %s (style=%s)' % (self.page.url, elem.attrs['style']))
                elem.attrs['style'] = css_parser().handle_css(self, self.page.url, elem.attrs['style'], True)

            if 'srcset' in elem.attrs:
                urls = elem.attrs['srcset'].strip()
                urls = urls.split(',')

                _urls = []
                for url in urls:
                    url = url.strip()
                    params = ''
                    if ' ' in url:
                        url, params = url.split(' ', 1)
                        params = ' ' + params

                    if url.startswith('blob:'):
                        url = url[5:]

                    if not (url.startswith('file:') or url.startswith('blob:') or url.startswith('about:') or url.startswith('data:')):
                        if self.crawl_policy.snapshot_exclude_element_re and re.match(self.crawl_policy.snapshot_exclude_element_re, elem.name):
                            logger.debug('download_asset %s excluded because it matches the element (%s) exclude regexp' % (url, elem.name))
                            url = reverse('html_excluded', args=(self.crawl_policy.id, 'element'))
                        else:
                            url = absolutize_url(self.page.url, url, True, True)
                            url = self.download_asset(url)
                            # Escape commas since they are used as a separator in srcset
                            url = url.replace(',', '%2C')

                    _urls.append(url + params)
                urls = ', '.join(_urls)
                elem['srcset'] = urls

            for attr in ('src', 'href'):
                if attr not in elem.attrs:
                    continue

                url = elem.attrs[attr]
                if url.startswith('blob:'):
                    url = url[5:]

                if not has_browsable_scheme(url):
                    continue

                url = absolutize_url(self.page.url, url, True, True)

                if elem.name in ('a', 'frame', 'iframe'):
                    elem.attrs[attr] = '/html/' + url
                    break
                else:
                    if self.crawl_policy.snapshot_exclude_element_re and re.match(self.crawl_policy.snapshot_exclude_element_re, elem.name):
                        logger.debug('download_asset %s excluded because it matches the element (%s) exclude regexp' % (url, elem.name))
                        filename_url = reverse('html_excluded', args=(self.crawl_policy.id, 'element'))
                    else:
                        filename_url = self.download_asset(url)
                    elem.attrs[attr] = filename_url

    def download_asset(self, url):
        if getattr(settings, 'TEST_HTML_ERROR_HANDLING', False) and url == 'http://127.0.0.1/test-exception':
            raise Exception('html_error_handling test')

        if self.crawl_policy.snapshot_exclude_url_re and re.match(self.crawl_policy.snapshot_exclude_url_re, url):
            logger.debug('download_asset %s excluded because it matches the url exclude regexp' % url)
            return reverse('html_excluded', args=(self.crawl_policy.id, 'url'))

        if url in self.asset_urls:
            for asset in self.assets:
                if asset.url == url:
                    return settings.SOSSE_HTML_SNAPSHOT_URL + asset.filename
            raise Exception('asset not found')

        logger.debug('download_asset %s' % url)
        mimetype = None
        extension = None
        page = None

        try:
            page = HTMLCache.download(url, settings.SOSSE_MAX_HTML_ASSET_SIZE)
            content = page.content
            mimetype = page.mimetype

            if mimetype == 'text/html':
                return '/html/' + url

            if self.crawl_policy.snapshot_exclude_mime_re and re.match(self.crawl_policy.snapshot_exclude_mime_re, mimetype):
                logger.debug('download_asset %s excluded because it matched the mimetype (%s) exclude regexp' % (url, mimetype))
                return reverse('html_excluded', args=(self.crawl_policy.id, 'mime'))

            if mimetype == 'text/css':
                logger.debug('handle_css of %s due to mimetype' % url)
                content = css_parser().handle_css(self, url, content, False).encode('utf-8')

        except CacheHit as e:
            logger.info('CACHE HIT %s', url)
            self._add_asset(e.asset)
            return settings.SOSSE_HTML_SNAPSHOT_URL + e.asset.filename
        except SkipIndexing as e:
            content = 'An error occured while downloading %s:\n%s' % (url, e.args[0])
            content = content.encode('utf-8')
            extension = '.txt'
        except:  # noqa
            content = 'An error occured while processing %s:\n%s' % (url, format_exc())
            content = content.encode('utf-8')
            extension = '.txt'
            if getattr(settings, 'TEST_MODE', False):
                raise

        assert isinstance(content, bytes)
        asset = HTMLCache.write_asset(url, content, page, extension=extension, mimetype=mimetype)
        if extension == '.html':
            return settings.SOSSE_HTML_SNAPSHOT_URL + asset

        self._add_asset(asset)
        return settings.SOSSE_HTML_SNAPSHOT_URL + asset.filename

    def get_asset_urls(self):
        return self.asset_urls
