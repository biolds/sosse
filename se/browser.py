# Copyright 2022-2025 Laurent Defert
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

import logging
import traceback
from time import sleep

from django.conf import settings
from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import HTTPError

from .utils import human_filesize

crawl_logger = logging.getLogger("crawler")


class AuthElemFailed(Exception):
    def __init__(self, page, *args, **kwargs):
        self.page = page
        super().__init__(*args, **kwargs)


class SkipIndexing(Exception):
    pass


class StalledDownload(SkipIndexing):
    def __init__(self):
        super().__init__("Download stalled")


class PageTooBig(SkipIndexing):
    def __init__(self, size, conf_size):
        size = human_filesize(size)
        conf_size = human_filesize(conf_size * 1024)
        super().__init__(
            f"Document size is too big ({size} > {conf_size}). You can increase the `max_file_size` and `max_html_asset_size` option in the configuration to index this file."
        )


class TooManyRedirects(SkipIndexing):
    def __init__(self):
        super().__init__(
            f"Max redirects ({settings.SOSSE_MAX_REDIRECTS}) reached. You can increase the `max_redirects` option in the configuration file in case it's needed."
        )


class Browser:
    inited = False

    @classmethod
    def init(cls):
        if cls.inited:
            return
        crawl_logger.debug(f"Browser {cls.__name__} init")
        cls._init()
        cls.inited = True

    @classmethod
    def destroy(cls):
        if not cls.inited:
            return
        crawl_logger.debug(f"Browser {cls.__name__} destroy")
        cls._destroy()
        cls.inited = False

    @classmethod
    def _init(cls):
        raise NotImplementedError()

    @classmethod
    def _destroy(cls):
        raise NotImplementedError()


def retry(f):
    def _retry(*args, **kwargs):
        count = 0
        while count <= settings.SOSSE_BROWSER_CRASH_RETRY:
            try:
                r = f(*args, **kwargs)
                crawl_logger.debug(f"{f} succeeded")
                return r
            except (WebDriverException, HTTPError):
                exc = traceback.format_exc()
                crawl_logger.error(f"{f} failed")
                crawl_logger.error(f"Selenium returned an exception:\n{exc}")

                cls = args[0]
                cls.destroy()
                sleep(settings.SOSSE_BROWSER_CRASH_SLEEP)
                cls.init()

                if count == settings.SOSSE_BROWSER_CRASH_RETRY:
                    raise
                count += 1
                crawl_logger.error(f"Retrying ({count} / {settings.SOSSE_BROWSER_CRASH_RETRY})")

    return _retry
