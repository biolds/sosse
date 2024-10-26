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
from io import BytesIO

from django.conf import settings
from linkpreview import Link, LinkPreview
from magic import from_buffer as magic_from_buffer
from PIL import Image


from .browser import Page, RequestBrowser
from .url import absolutize_url


class DocumentMeta:
    @classmethod
    def get_preview_url(cls, page: Page) -> str:
        soup = page.get_soup()
        link = Link(page.url)
        link_preview = LinkPreview(link, None, soup)

        if link_preview.image:
            yield link_preview.image

        for attr in ('image', 'description'):
            url: str = getattr(link_preview, attr)

            if url is None:
                continue

            if url.startswith(('http:', 'https:', ':/', '/')) and ' ' in url:
                yield url.split(' ', 1)[0]

    @classmethod
    def create_preview(cls, page: Page, crawl_policy, image_name: str) -> str | None:
        for url in cls.get_preview_url(page):
            url = absolutize_url(page.url, url)

            img_page = RequestBrowser.get(url, headers={
                'User-Agent': settings.SOSSE_USER_AGENT,
                'Accept': 'image/*',
            })

            if img_page.status_code != 200:
                continue

            mimetype = magic_from_buffer(img_page.content, mime=True)
            if not mimetype.startswith('image/'):
                continue

            thumb_jpg = os.path.join(settings.SOSSE_THUMBNAILS_DIR, image_name + '.jpg')
            dir_name = os.path.dirname(thumb_jpg)
            os.makedirs(dir_name, exist_ok=True)

            with Image.open(BytesIO(img_page.content)) as img:
                img = img.convert('RGB')  # Remove alpha channel from the png
                img.thumbnail((160, 100))
                img.save(thumb_jpg, 'jpeg')

            return thumb_jpg