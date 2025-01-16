# Copyright 2025 Laurent Defert
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

import json
import os

from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromiumOptions

from .browser_selenium import BrowserSelenium
from .domain_setting import user_agent


class BrowserChromium(BrowserSelenium):
    DRIVER_CLASS = webdriver.Chrome
    name = "chromium"

    CONTENT_HANDLERS = (
        # Video
        b"""<html>
<head>
<meta name="viewport" content="width=device-width"/?>
</head>
<body>
<video controls="" autoplay="" name="media">
<source src="(?P<url>[^"]+)" type="[^"]+"/?>
</video>
</body>
</html>""".replace(b"\n", b""),
        # Image
        b"""<html style="height: 100%;">
<head>
<meta ((content="width=device-width, minimum-scale=0.1"|name="viewport") ?){2}/?>
<title>[^<]*</title>
</head>
<body style="margin: 0px; height: 100%; background-color: rgb\\(14, 14, 14\\);">
<img .*src="(?P<url>[^"]+)".*/?>
</body>
</html>""".replace(b"\n", b""),
    )

    @classmethod
    def _get_options_obj(cls):
        options = ChromiumOptions()
        options.binary_location = "/usr/bin/chromium"
        prefs = {
            "profile.default_content_settings.popups": 0,
            "download.default_directory": cls._get_download_dir(),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        }
        options.add_experimental_option("prefs", prefs)
        return options

    @classmethod
    def _get_options(cls):
        opts = []
        if settings.SOSSE_PROXY:
            opts.append(f"--proxy-server={settings.SOSSE_PROXY.rstrip('/')}")
        opts.append(f"--user-agent={user_agent()}")
        opts.append("--start-maximized")
        opts.append("--start-fullscreen")
        return opts

    @classmethod
    def _get_driver(cls, options):
        return webdriver.Chrome(options=options)

    @classmethod
    def _driver_get(cls, url, force_reload=False):
        _url = json.dumps(url)
        if cls.driver.execute_script(f"return window.location.href === {_url}") and not force_reload:
            return
        dl_dir_files = cls.page_change_wait_setup()
        cls.driver.get(url)
        cls.page_change_wait(dl_dir_files)

    @classmethod
    def _get_download_file(cls):
        d = os.listdir(cls._get_download_dir())
        d = [x for x in d if not x.startswith(".")]
        if len(d) == 0:
            return None
        return os.path.join(cls._get_download_dir(), d[0])

    @classmethod
    def _get_download_dir(cls):
        return settings.SOSSE_TMP_DL_DIR + "/chromium/" + str(cls._worker_no)
