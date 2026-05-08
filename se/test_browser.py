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
from .browser_firefox import BrowserFirefox
from .models import BrowserConfig
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


class BrowserConfigTest(TransactionTestCase):
    def tearDown(self):
        BrowserChromium.inited = False
        BrowserChromium._browser_config_key = None
        BrowserFirefox.inited = False
        BrowserFirefox._browser_config_key = None
        super().tearDown()

    def test_chromium_ignore_ssl_errors_sets_command_line_flag(self):
        BrowserConfig.objects.update_or_create(
            browser=BrowserConfig.BROWSER_CHROMIUM,
            defaults={"ignore_ssl_errors": True},
        )

        opts = BrowserChromium._configured_options()

        self.assertIn("--ignore-certificate-errors", opts)

    def test_firefox_ignore_ssl_errors_sets_selenium_capability(self):
        BrowserConfig.objects.update_or_create(
            browser=BrowserConfig.BROWSER_FIREFOX,
            defaults={"ignore_ssl_errors": True},
        )
        options = mock.Mock()

        BrowserFirefox._configure_options_obj(options)

        options.set_capability.assert_called_once_with("acceptInsecureCerts", True)

    def test_browser_extra_options_are_appended(self):
        BrowserConfig.objects.update_or_create(
            browser=BrowserConfig.BROWSER_CHROMIUM,
            defaults={"extra_options": "--foo --bar=baz"},
        )

        opts = BrowserChromium._configured_options()

        self.assertIn("--foo", opts)
        self.assertIn("--bar=baz", opts)

    def test_selenium_config_change_restarts_browser(self):
        BrowserChromium.inited = True
        BrowserChromium._browser_config_key = (False, "")
        BrowserConfig.objects.update_or_create(
            browser=BrowserConfig.BROWSER_CHROMIUM,
            defaults={"ignore_ssl_errors": True},
        )

        with mock.patch.object(BrowserChromium, "destroy") as destroy:
            BrowserChromium._ensure_current_config()

        destroy.assert_called_once()

    def test_selenium_unchanged_config_keeps_browser(self):
        BrowserChromium.inited = True
        BrowserChromium._browser_config_key = (False, "")
        BrowserConfig.objects.update_or_create(
            browser=BrowserConfig.BROWSER_CHROMIUM,
            defaults={"ignore_ssl_errors": False, "extra_options": ""},
        )

        with mock.patch.object(BrowserChromium, "destroy") as destroy:
            BrowserChromium._ensure_current_config()

        destroy.assert_not_called()
