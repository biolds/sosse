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

import json
import os
from urllib.parse import urlparse

import psutil
import selenium
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from .browser_selenium import BrowserSelenium
from .domain import user_agent


class BrowserFirefox(BrowserSelenium):
    DRIVER_CLASS = webdriver.Firefox
    name = "firefox"

    # img tag matches on 2 or 3 match because class="transparent" is set for PNG, but not for JPEG
    CONTENT_HANDLERS = (
        b"""<html>
<head>
<meta name="viewport" content="width=device-width; height=device-height;">
<link rel="stylesheet" href="resource://content-accessible/ImageDocument.css">
<link rel="stylesheet" href="resource://content-accessible/TopLevelImageDocument.css">
<title>[^<]*</title>
</head>
<body>
<img ((src="(?P<url>[^"]+)"|alt="[^"]+"|class="transparent") ?){2,3}>
</body>
</html>""".replace(b"\n", b""),
    )

    @classmethod
    def _get_options_obj(cls):
        options = FirefoxOptions()
        options.set_preference(
            "browser.download.dir",
            settings.SOSSE_TMP_DL_DIR + "/firefox/" + str(cls._worker_no),
        )
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.useDownloadDir", True)
        options.set_preference("browser.download.viewableInternally.enabledTypes", "")
        options.set_preference("browser.helperApps.alwaysAsk.force", False)
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk",
            "application/pdf;text/plain;application/text;text/xml;application/xml;application/octet-stream",
        )
        options.set_preference("general.useragent.override", user_agent())

        # Ensure more secure cookie defaults, and be cosistent with Chromium's behavior
        # See https://hacks.mozilla.org/2020/08/changes-to-samesite-cookie-behavior/
        options.set_preference("network.cookie.sameSite.laxByDefault", True)
        options.set_preference("network.cookie.sameSite.noneRequiresSecure", True)
        options.set_preference("pdfjs.disabled", True)
        options.set_preference("media.play-stand-alone", False)

        if settings.SOSSE_PROXY:
            url = urlparse(settings.SOSSE_PROXY)
            url, port = url.netloc.rsplit(":", 1)
            port = int(port)
            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.http", url)
            options.set_preference("network.proxy.http_port", port)
            options.set_preference("network.proxy.ssl", url)
            options.set_preference("network.proxy.ssl_port", port)
        return options

    @classmethod
    def _get_options(cls):
        return []

    @classmethod
    def _get_driver(cls, options):
        log_file = f"/var/log/sosse/geckodriver-{cls._worker_no}.log"

        selenium_ver = tuple(map(int, selenium.__version__.split(".")))
        if selenium_ver < (4, 9, 0):
            service = {"service_log_path": log_file}
        elif selenium_ver < (4, 24, 0):
            service = {"service": FirefoxService(log_output=log_file)}
        else:
            service = {"service": FirefoxService(log_output=log_file, executable_path="/usr/local/bin/geckodriver")}
        return webdriver.Firefox(options=options, **service)

    @classmethod
    def _driver_get(cls, url, force_reload=False):
        _url = json.dumps(url)
        if cls.driver().execute_script(f"return window.location.href === {_url}") and not force_reload:
            return
        dl_dir_files = cls.page_change_wait_setup()
        # Work-around to https://github.com/SeleniumHQ/selenium/issues/4769
        # When a download starts, the regular cls.driver().get call is stuck
        cls.driver().execute_script(
            f"""
            window.location.assign({_url});
        """
        )

        if url == "about:blank":
            raise Exception("navigating to about:blank")

        cls.page_change_wait(dl_dir_files)

    @classmethod
    def _destroy(cls):
        # Kill firefox, otherwise it can get stuck on a confirmation dialog
        # (ie, when a download is still running)
        gecko_pid = cls._driver.service.process.pid
        p = psutil.Process(gecko_pid)
        p.children()[0].kill()
        super()._destroy()

    @classmethod
    def _get_download_dir(cls):
        return settings.SOSSE_TMP_DL_DIR + "/firefox/" + str(cls._worker_no)

    @classmethod
    def _get_download_file(cls):
        for f in os.listdir(cls._get_download_dir()):
            if f.endswith(".part"):
                break
        else:
            d = os.listdir(cls._get_download_dir())
            if len(d) == 0:
                return None
            return os.path.join(cls._get_download_dir(), d[0])
        return os.path.join(cls._get_download_dir(), f)
