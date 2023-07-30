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
import os
import re

from hashlib import md5
from mimetypes import guess_extension
from urllib.parse import quote, unquote_plus, urlparse
from traceback import format_exc

import cssutils
from django.conf import settings
from django.shortcuts import reverse

logger = logging.getLogger('html_snapshot')

HTML_SNAPSHOT_HASH_LEN = 10


def max_filename_size():
    return os.statvfs(settings.SOSSE_HTML_SNAPSHOT_DIR).f_namemax


class HTMLSnapshot:
    def __init__(self, page, crawl_policy):
        self.page = page
        self.crawl_policy = crawl_policy

    def snapshot(self, _hash):
        logger.debug('snapshot of %s' % self.page.url)
        self.sanitize()
        self.handle_assets()
        self.write_asset(self.page.url, self.page.dump_html(), '.html', _hash)
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
                    elem.string = self.handle_css(self.page.url, elem.string, False)

            if elem.attrs.get('style'):
                logger.debug('handle_css of %s (style=)' % self.page.url)
                elem.attrs['style'] = self.handle_css(self.page.url, elem.attrs['style'], True)

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

                if url.startswith('file:') or url.startswith('blob:') or url.startswith('about:') or url.startswith('data:'):
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

    def handle_css(self, src_url, content, inline_css):
        from .document import absolutize_url
        if inline_css:
            sheet = cssutils.parseStyle(content)
        else:
            sheet = cssutils.parseString(content)
        for rule in sheet:
            if not hasattr(rule, 'style'):
                continue

            for prop in rule.style:
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
                            url = self.download_asset(url)

                        if has_quotes:
                            url = f'"{url}"'

                        val += f'url({url})'

                    val += value[m[-1].end(0):]
                    prop.value = val
        css = sheet.cssText
        if not inline_css:
            css = css.decode('utf-8')
        return css

    def download_asset(self, url):
        if self.crawl_policy.snapshot_exclude_url_re and re.match(self.crawl_policy.snapshot_exclude_url_re, url):
            logger.debug('download_asset %s excluded because it matches the url exclude regexp' % url)
            return reverse('html_excluded', args=(self.crawl_policy.id, 'url'))

        from .browser import RequestBrowser, SkipIndexing
        logger.debug('download_asset %s' % url)
        try:
            asset = RequestBrowser.get(url, raw=True, check_status=True,
                                       max_file_size=settings.SOSSE_MAX_HTML_ASSET_SIZE, headers={'Accept': '*/*'})
            content = asset.content

            if asset.mimetype == 'text/html':
                return '/html/' + url

            if self.crawl_policy.snapshot_exclude_mime_re and re.match(self.crawl_policy.snapshot_exclude_mime_re, asset.mimetype):
                logger.debug('download_asset %s excluded because it matched the mimetype (%s) exclude regexp' % (url, asset.mimetype))
                return reverse('html_excluded', args=(self.crawl_policy.id, 'mime'))

            # Build the extension using mimetypes, because the appropriate extension
            # is required by Nginx when the file is served statically
            extension = guess_extension(asset.mimetype)
            if extension is None:
                _, ext = url.rsplit('.', 1)
                if '?' in ext:
                    ext, _ = ext.split('?', 1)

                if '/' in ext:
                    extension = '.bin'
                else:
                    extension = f'.{ext}'

            if asset.mimetype == 'text/css':
                logger.debug('handle_css of %s due to mimetype' % url)
                content = self.handle_css(url, content, False).encode('utf-8')
        except SkipIndexing as e:
            content = 'An error occured while downloading %s:\n%s' % (url, e.args[0])
            content = content.encode('utf-8')
            extension = '.txt'
        except:  # noqa
            content = 'An error occured while downloading %s:\n%s' % (url, format_exc())
            content = content.encode('utf-8')
            extension = '.txt'
            if getattr(settings, 'TEST_MODE', False):
                raise

        return self.write_asset(url, content, extension)

    @staticmethod
    def html_filename(url, _hash, extension):
        from .document import sanitize_url
        url = sanitize_url(url, True, True)
        _url = urlparse(url)

        filename = _url.path
        if '/' in _url.path:
            _, filename = _url.path.rsplit('/', 1)

        url = url.replace('//', '/')
        # Unquote before requoting
        url = unquote_plus(url)
        # Replace % by , to prevent interpration of the escape by nginx
        url = quote(url).replace('%', ',')

        # Make sure the filename is not longer than supported by the filesystem
        parts = url.split('/')
        _parts = []
        for no, part in enumerate(parts):
            if no == len(parts) - 1:
                max_len = max_filename_size() - HTML_SNAPSHOT_HASH_LEN - len(extension) - 1
                if len(part) > max_len:
                    part = part[:max_len]
                part = f'{part}_{_hash}{extension}'
            else:
                if len(part) > max_filename_size():
                    part = part[:max_filename_size() - HTML_SNAPSHOT_HASH_LEN - 1]
                    part = f'{part}_{_hash}'

            _parts.append(part)
        return '/'.join(_parts)

    def write_asset(self, url, content, extension, _hash=None):
        logger.debug('html_write_asset for %s', url)
        _hash = _hash or md5(content).hexdigest()[:HTML_SNAPSHOT_HASH_LEN]
        filename_url = self.html_filename(url, _hash, extension)
        dest = os.path.join(settings.SOSSE_HTML_SNAPSHOT_DIR, filename_url)

        dest_dir, _ = dest.rsplit('/', 1)
        os.makedirs(dest_dir, 0o755, exist_ok=True)

        with open(dest, 'wb') as fd:
            fd.write(content)
        return settings.SOSSE_HTML_SNAPSHOT_URL + filename_url
