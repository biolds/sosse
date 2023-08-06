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

from requests import HTTPError

from .browser import Page, PageTooBig


class BrowserMock:
    def __init__(self, web):
        self.web = {
            # Crawler tests
            'http://127.0.0.1/robots.txt': HTTPError(),
            'http://127.0.0.1/favicon.ico': HTTPError(),
            'http://127.0.0.2/robots.txt': HTTPError(),
            'http://127.0.0.2/favicon.ico': HTTPError(),
            'http://127.0.0.3/robots.txt': HTTPError(),
            'http://127.0.0.3/favicon.ico': HTTPError(),

            # HTML snapshot tests
            'http://127.0.0.1/style.css': b'body {\n    color: #fff\n    }',
            'http://127.0.0.1/page.html': b'HTML test',
            'http://127.0.0.1/image.png': b'PNG test',
            'http://127.0.0.1/image2.png': b'PNG test2',
            'http://127.0.0.1/image3.png': b'PNG test3',
            'http://127.0.0.1/image.jpg': b'JPG test',
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
