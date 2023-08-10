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

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import models

logger = logging.getLogger('html_snapshot')


def remove_html_asset_file(fn):
    try:
        logger.debug('deleting %s', fn)
        os.unlink(fn)
    except OSError:
        # should not happen
        pass
    try:
        dn = os.path.dirname(fn)
        logger.debug('rmdir start %s', dn)
        while dn.startswith(settings.SOSSE_HTML_SNAPSHOT_DIR):
            logger.debug('rmdir %s', dn)
            os.rmdir(dn)
            dn = os.path.dirname(dn)
    except OSError:
        # ignore directory not empty errors
        pass


class HTMLAsset(models.Model):
    url = models.TextField(unique=True)
    filename = models.TextField()
    ref_count = models.PositiveBigIntegerField(default=0)

    @staticmethod
    def add_ref(url, fn):
        logger.debug('addref %s %s', url, fn)
        # TODO: fix the race condition below
        asset, created = HTMLAsset.objects.get_or_create(url=url, filename=fn)

        if created:
            max_ref_count = HTMLAsset.objects.filter(filename=fn).aggregate(models.Max('ref_count'))
            max_ref_count = max_ref_count.get('ref_count__max') or 0
            HTMLAsset.objects.filter(id=asset.id).update(ref_count=max_ref_count)

        # multiple URLs can be stored with the same filename, in this case the ref_count
        # must be incremented for each entry, that's why the filtering is done on ``filneame``
        count = HTMLAsset.objects.filter(filename=fn).update(ref_count=models.F('ref_count') + 1)
        logger.debug('%s refcount incremented for %s', count, fn)

    @staticmethod
    def html_delete(url, _hash):
        from .document import sanitize_url
        from .html_snapshot import HTMLSnapshot
        url = sanitize_url(url, True, True)
        fn = settings.SOSSE_HTML_SNAPSHOT_DIR + HTMLSnapshot.html_filename(url, _hash, '.html')
        try:
            content = open(fn, 'rb').read()
            assets = HTMLAsset.html_extract_assets(content)
            for asset in assets:
                HTMLAsset.remove_ref(asset)
        except OSError:
            pass

        remove_html_asset_file(fn)

    @staticmethod
    def remove_ref(fn):
        # TODO: fix the race condition below
        logger.debug('removing ref on %s', fn)
        HTMLAsset.objects.filter(filename=fn).update(ref_count=models.F('ref_count') - 1)

        refs_count = HTMLAsset.objects.filter(filename=fn, ref_count__gt=0).aggregate(models.Sum('ref_count'))
        refs_count = refs_count.get('ref_count__sum')

        # refs_count is None when HTMLAsset.objects.filter(...) returns an empty set
        if refs_count is None or refs_count <= 0:
            logger.debug('removing file %s', fn)
            remove_html_asset_file(settings.SOSSE_HTML_SNAPSHOT_DIR + fn)

        HTMLAsset.objects.filter(filename=fn, ref_count__lte=0).delete()

    @staticmethod
    def html_extract_assets(content):
        from .html_snapshot import css_parser
        assets = set()
        soup = BeautifulSoup(content, 'html5lib')
        for elem in soup.find_all(True):
            if elem.name == 'style':
                if elem.string:
                    assets |= css_parser().css_extract_assets(elem.string, False)

            if elem.attrs.get('style'):
                assets |= css_parser().css_extract_assets(elem.attrs['style'], True)

            if 'srcset' in elem.attrs:
                urls = elem.attrs['srcset'].strip()
                urls = urls.split(',')

                for url in urls:
                    url = url.strip()
                    if ' ' in url:
                        url, _ = url.split(' ', 1)

                    # unescape comma that were in HTMLSnapshot.handle_assets
                    url = url.replace('%2C', ',')

                    if url.startswith(settings.SOSSE_HTML_SNAPSHOT_URL):
                        assets.add(url[len(settings.SOSSE_HTML_SNAPSHOT_URL):])

            for attr in ('src', 'href'):
                if attr not in elem.attrs:
                    continue

                url = elem.attrs[attr]
                if url.startswith(settings.SOSSE_HTML_SNAPSHOT_URL):
                    filename = url[len(settings.SOSSE_HTML_SNAPSHOT_URL):]
                    assets.add(filename)

                    if url.endswith('.css'):
                        filename = settings.SOSSE_HTML_SNAPSHOT_DIR + filename
                        assets |= css_parser().css_extract_assets(open(filename).read(), False)

        return assets
