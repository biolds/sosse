# Copyright 2024 Laurent Defert
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
from base64 import b64decode
from io import BytesIO

from django.conf import settings
from linkpreview import Link, LinkPreview
from magic import from_buffer as magic_from_buffer
from PIL import Image, UnidentifiedImageError


from .browser import Page, RequestBrowser
from .url import absolutize_url


class DocumentMeta:
    @classmethod
    def get_preview_urls(cls, page: Page) -> str:
        soup = page.get_soup()
        link = Link(page.url)
        link_preview = LinkPreview(link, None, soup)

        if link_preview.image:
            yield link_preview.image

        for attr in ('image', 'description'):
            url: str | None = getattr(link_preview, attr)

            if url is None:
                continue

            if url.startswith(('http:', 'https:', ':/', '/')) and ' ' in url:
                yield url.split(' ', 1)[0]

    @classmethod
    def preview_file_from_url(cls, url: str, image_name: str) -> str | None:
        if url.startswith('blob:'):
            return

        if url.startswith('data:'):
            content = url.lstrip('data:')
            if not content.startswith('image/'):
                return
            mimetype, content = content.split(',', 1)

            if not mimetype.endswith(';base64'):
                return

            content = b64decode(content)
        else:
            img_page = RequestBrowser.get(url, headers={
                'User-Agent': settings.SOSSE_USER_AGENT,
                'Accept': 'image/*',
            })

            if img_page.status_code != 200:
                return

            mimetype = magic_from_buffer(img_page.content, mime=True)
            if not mimetype.startswith('image/'):
                return
            content = img_page.content

        thumb_jpg = os.path.join(
            settings.SOSSE_THUMBNAILS_DIR, image_name + '.jpg')
        dir_name = os.path.dirname(thumb_jpg)
        os.makedirs(dir_name, exist_ok=True)

        try:
            with Image.open(BytesIO(content)) as img:
                # Remove alpha channel from the png
                img = img.convert('RGB')
                img.thumbnail((160, 100))
                img.save(thumb_jpg, 'jpeg')
        except UnidentifiedImageError:
            return

        return thumb_jpg

    @classmethod
    def create_preview(cls, page: Page, image_name: str) -> str | None:
        for url in cls.get_preview_urls(page):
            if url.startswith('blob:'):
                continue
            url = absolutize_url(page.url, url)
            preview_file = cls.preview_file_from_url(url, image_name)
            if preview_file:
                return preview_file
