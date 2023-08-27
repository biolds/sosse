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

from datetime import timedelta
from hashlib import md5
from mimetypes import guess_extension
from urllib.parse import quote, unquote_plus

from django.conf import settings
from django.utils import timezone

from .browser import RequestBrowser
from .html_asset import HTMLAsset
from .url import sanitize_url
from .utils import http_date_format


logger = logging.getLogger('html_snapshot')

# https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#heuristic_caching
HEURISTIC_CACHE_THRESHOLD_PERCENT = 10
HTML_SNAPSHOT_HASH_LEN = 10


def max_filename_size():
    return os.statvfs(settings.SOSSE_HTML_SNAPSHOT_DIR).f_namemax


class CacheHit(Exception):
    def __init__(self, asset):
        self.asset = asset


class CacheMiss(Exception):
    pass


class CacheRefresh(Exception):
    def __init__(self, page):
        self.page = page


class HTMLCache():
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#expires_or_max-age
    @staticmethod
    def _max_age_check(asset, max_file_size):
        if (asset.max_age and asset.last_modified) or asset.etag:
            if asset.max_age and asset.last_modified and asset.last_modified + timedelta(seconds=asset.max_age) >= timezone.now():
                logger.debug('cache hit, max_age')
                raise CacheHit(asset)
            else:
                logger.debug('cache miss, max_age, %s + %s > %s', asset.last_modified, asset.max_age, timezone.now())

                # https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#validation
                if not asset.has_cache_control:
                    logger.debug('cache miss, max_age, no cache control')
                    raise CacheMiss()

                headers = {
                    'Accept': '*/*',
                    'If-Modified-Since': http_date_format(asset.download_date)
                }

                if asset.etag:
                    headers['If-None-Match'] = asset.etag

                page = RequestBrowser.get(asset.url,
                                          check_status=True,
                                          max_file_size=max_file_size,
                                          headers=headers)

                if page.status_code == 304:
                    # http not modified
                    logger.debug('cache hit, max_age, cache control, not modified')
                    raise CacheHit(asset)

                logger.debug('cache refresh, max_age, cache control, refresh')
                raise CacheRefresh(page)

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#heuristic_caching
    @staticmethod
    def _heuristic_check(asset):
        if asset.download_date and asset.last_modified:
            dt = asset.download_date - asset.last_modified
            dt = (dt.total_seconds() * HEURISTIC_CACHE_THRESHOLD_PERCENT) / 100
            dt = timedelta(seconds=dt)
            if asset.download_date + dt > timezone.now():
                logger.debug('cache hit, heuristic_caching')
                raise CacheHit(asset)
            else:
                logger.debug('cache miss, heuristic_caching, %s + %s < %s', asset.download_date, dt, timezone.now())
                raise CacheMiss()

    @staticmethod
    def _cache_check(url, max_file_size):
        asset = HTMLAsset.objects.filter(url=url).order_by('download_date').last()

        if not asset:
            logger.debug('cache miss, asset does not exist')
            raise CacheMiss()

        if asset.download_date is None:
            logger.debug('cache miss, force refresh')
            raise CacheMiss()

        HTMLCache._max_age_check(asset, max_file_size)
        HTMLCache._heuristic_check(asset)
        logger.debug('cache miss, cache outdated')
        raise CacheMiss()

    @staticmethod
    def download(url, max_file_size):
        try:
            HTMLCache._cache_check(url, max_file_size)
        except CacheHit as e:
            e.asset.increment_ref()
            raise
        except CacheRefresh as e:
            return e.page
        except CacheMiss:
            pass

        page = RequestBrowser.get(url,
                                  check_status=True,
                                  max_file_size=max_file_size,
                                  headers={'Accept': '*/*'})
        return page

    @staticmethod
    def create_cache_entry(url, filename, page=None):
        asset, created = HTMLAsset.objects.get_or_create(url=url, filename=filename)

        if created:
            asset.init_ref_count()

        asset.increment_ref()

        if page:
            asset.update_from_page(page)

        return asset

    @staticmethod
    def write_asset(url, content, page, extension=None, mimetype=None):
        assert isinstance(content, bytes)

        logger.debug('html_write_asset for %s', url)
        _hash = md5(content).hexdigest()[:HTML_SNAPSHOT_HASH_LEN]

        # Build the extension using mimetypes, because the appropriate extension
        # is required by Nginx when the file is served statically
        if extension is None:
            assert mimetype is not None
            extension = guess_extension(mimetype)
            if extension is None:
                _, ext = url.rsplit('.', 1)
                if '?' in ext:
                    ext, _ = ext.split('?', 1)

                if '/' in ext:
                    extension = '.bin'
                else:
                    extension = f'.{ext}'

        url = sanitize_url(url)
        filename_url = HTMLCache.html_filename(url, _hash, extension)
        dest = os.path.join(settings.SOSSE_HTML_SNAPSHOT_DIR, filename_url)
        dest_dir, _ = dest.rsplit('/', 1)
        os.makedirs(dest_dir, 0o755, exist_ok=True)

        with open(dest, 'wb') as fd:
            fd.write(content)

        return HTMLCache.create_cache_entry(url, filename_url, page)

    @staticmethod
    def html_filename(url, _hash, extension):
        assert extension.startswith('.')

        # replace http:// by http:/
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
