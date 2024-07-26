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


from django.test import TransactionTestCase

from .document_meta import DocumentMeta
from .browser import Page


class DocumentMetaTest(TransactionTestCase):
    def test_ogp_image(self):
        page = Page('http://127.0.0.1/', b'''
            <html prefix="og: https://ogp.me/ns#">
                <head>
                    <meta property="og:image" content="https://ia.media-imdb.com/images/rock.jpg" />
                </head>
            </html>
        ''', None)
        image_url = list(DocumentMeta.get_preview_url(page))
        self.assertEqual(image_url, ['https://ia.media-imdb.com/images/rock.jpg'])

    def test_twitter_image(self):
        page = Page('http://127.0.0.1/', b'''
            <html>
                <head>
                    <meta name="twitter:image" content="http://graphics8.nytimes.com/images/2012/02/19/us/19whitney-span/19whitney-span-articleLarge.jpg">
                </head>
            </html>
        ''', None)
        image_url = list(DocumentMeta.get_preview_url(page))
        self.assertEqual(image_url, ['http://graphics8.nytimes.com/images/2012/02/19/us/19whitney-span/19whitney-span-articleLarge.jpg'])
