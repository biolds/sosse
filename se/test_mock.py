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

import re
from base64 import b64decode
from mimetypes import guess_type

from requests import HTTPError

from .browser import Page, PageTooBig


PNG64 = '''
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9
kT1Iw0AcxV9TxSqVDnYQUchQneziF461CkWoUGqFVh1MLv2CJg1Jiouj4Fpw8GOx6uDirKuDqyAI
foC4ujgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kgw1eyKAapmGelEXMzmVsWeVwQQQi+mMSIxU59LpZLw
HF/38PH1LsqzvM/9OfqVvMkAn0gcY7phEW8Qz2xaOud94jArSQrxOfG4QRckfuS67PIb56LDAs8M
G5n0PHGYWCx2sNzBrGSoxFPEEUXVKF/Iuqxw3uKsVmqsdU/+wmBeW1nmOs1hJLCIJaQgQkYNZVRg
IUqrRoqJNO3HPfxDjj9FLplcZTByLKAKFZLjB/+D392ahckJNykYB7pfbPtjFOjZBZp12/4+tu3m
CeB/Bq60tr/aAGY/Sa+3tcgRENoGLq7bmrwHXO4Ag0+6ZEiO5KcpFArA+xl9Uw4YuAX61tzeWvs4
fQAy1FXyBjg4BMaKlL3u8e5AZ2//nmn19wO39nLC/XngKAAAAAlwSFlzAAAuIwAALiMBeKU/dgAA
AAd0SU1FB+cIDwk1OsRq+oYAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAAA
DElEQVQI12P4//8/AAX+Av7czFnnAAAAAElFTkSuQmCC
'''


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
            'http://127.0.0.1/image.png': b64decode(PNG64),
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

    def __call__(self, url, check_status=False, **kwargs):
        content = self.web[url]
        if isinstance(content, Exception):
            raise content
        headers = None
        status_code = None
        if isinstance(content, tuple):
            if len(content) == 2:
                content, headers = content
            else:
                content, headers, status_code = content

        mimetype = guess_type(url)[0]
        return Page(url, content, BrowserMock, mimetype, headers, status_code)


class BrowserTest:
    def _check_key_val(self, key, val, content):
        raise NotImplementedError()


class CleanTest(BrowserTest):
    def _check_key_val(self, key, val, content):
        s = b'"%s": %s' % (key, val)
        self.assertIn(s, content)


class FirefoxTest(BrowserTest):
    def _check_key_val(self, key, val, _content):
        s = b'%s%s' % (key, val)
        content = re.sub(b'<[^>]*>', b'', _content)
        found = s in content

        s = b'"%s": %s' % (key, val)
        found |= s in content

        self.assertTrue(found, '"%s" not found in\n%s' % (s, _content))
