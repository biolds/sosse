# Copyright 2026 Laurent Defert
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

from django.apps import apps
from django.db import DatabaseError


def get_browser_config(browser):
    try:
        browser_config = apps.get_model("se", "BrowserConfig")
        return browser_config.objects.filter(browser=browser).first()
    except (LookupError, DatabaseError):
        return None


def config_key(browser):
    config = get_browser_config(browser)
    if not config:
        return False, ""
    return config.ignore_ssl_errors, config.extra_options


def ignore_ssl_errors(browser):
    return config_key(browser)[0]


def extra_options(browser):
    return config_key(browser)[1]
