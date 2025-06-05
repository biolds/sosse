# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

from unittest import mock

from django.test import TransactionTestCase

from .browser_chromium import BrowserChromium
from .test_mock import BrowserMock


def html_content(content: str) -> str:
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    return b"".join(lines)


class ChromiumTest(TransactionTestCase):
    IMG_CONTENT = html_content(b"""
        <html style="height: 100%;">
            <head>
                <meta content="width=device-width, minimum-scale=0.1" name="viewport"/>
                <title>DSC_1350.JPG (4000\xc3\x973000)</title>
            </head>
            <body style="margin: 0px; height: 100%; background-color: rgb(14, 14, 14);">
                <img height="2108" src="http://192.168.119.27:4567/uploads/PC/DSC_1350.JPG" style="
                display: block;-webkit-user-select: none;margin: auto;cursor: zoom-in;background-color: hsl(0, 0%, 90%);
                transition: background-color 300ms;" width="2810"/>
            </body>
        </html>
    """)

    @mock.patch("se.browser_request.BrowserRequest.get")
    def test_chromium_inline_image(self, BrowserRequest):
        BrowserRequest.side_effect = BrowserMock(
            {"http://192.168.119.27:4567/uploads/PC/DSC_1350.JPG": b"Image content"}
        )

        content = BrowserChromium._escape_content_handler(self.IMG_CONTENT)
        self.assertEqual(content, b"Image content")
