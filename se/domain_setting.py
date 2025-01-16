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

import logging
import re
from hashlib import md5
from urllib.parse import urlparse

import fake_useragent
import requests
from django.conf import settings
from django.db import models

from .browser import TooManyRedirects

crawl_logger = logging.getLogger("crawler")
UA_STR = None


def user_agent():
    global UA_STR
    if UA_STR:
        return UA_STR

    if settings.SOSSE_USER_AGENT:
        UA_STR = settings.SOSSE_USER_AGENT
    else:
        fua_params = {}
        if settings.SOSSE_FAKE_USER_AGENT_BROWSER:
            fua_params["browsers"] = settings.SOSSE_FAKE_USER_AGENT_BROWSER
        if settings.SOSSE_FAKE_USER_AGENT_OS:
            fua_params["os"] = settings.SOSSE_FAKE_USER_AGENT_OS
        if settings.SOSSE_FAKE_USER_AGENT_PLATFORM:
            fua_params["platforms"] = settings.SOSSE_FAKE_USER_AGENT_PLATFORM

        fua = fake_useragent.UserAgent(**fua_params)
        UA_STR = fua.random
    return UA_STR


class DomainSetting(models.Model):
    BROWSE_DETECT = "detect"
    BROWSE_CHROMIUM = "selenium"
    BROWSE_FIREFOX = "firefox"
    BROWSE_REQUESTS = "requests"
    BROWSE_MODE = [
        (BROWSE_DETECT, "Detect"),
        (BROWSE_CHROMIUM, "Chromium"),
        (BROWSE_FIREFOX, "Firefox"),
        (BROWSE_REQUESTS, "Python Requests"),
    ]

    ROBOTS_UNKNOWN = "unknown"
    ROBOTS_EMPTY = "empty"
    ROBOTS_LOADED = "loaded"

    ROBOTS_STATUS = [
        (ROBOTS_UNKNOWN, "Unknown"),
        (ROBOTS_EMPTY, "Empty"),
        (ROBOTS_LOADED, "Loaded"),
    ]

    ROBOTS_TXT_USER_AGENT = "user-agent"
    ROBOTS_TXT_ALLOW = "allow"
    ROBOTS_TXT_DISALLOW = "disallow"
    ROBOTS_TXT_KEYS = (ROBOTS_TXT_USER_AGENT, ROBOTS_TXT_ALLOW, ROBOTS_TXT_DISALLOW)

    UA_HASH = None

    browse_mode = models.CharField(max_length=10, choices=BROWSE_MODE, default=BROWSE_DETECT)
    domain = models.TextField(unique=True)

    robots_status = models.CharField(
        max_length=10,
        choices=ROBOTS_STATUS,
        default=ROBOTS_UNKNOWN,
        verbose_name="robots.txt status",
    )
    robots_ua_hash = models.CharField(max_length=32, default="", blank=True)
    robots_allow = models.TextField(default="", blank=True, verbose_name="robots.txt allow rules")
    robots_disallow = models.TextField(default="", blank=True, verbose_name="robots.txt disallow rules")
    ignore_robots = models.BooleanField(default=False, verbose_name="Ignore robots.txt")

    def __str__(self):
        return self.domain

    @classmethod
    def ua_hash(cls):
        if cls.UA_HASH is None:
            ua = user_agent()
            if ua is not None:
                cls.UA_HASH = md5(ua.encode("ascii"), usedforsecurity=False).hexdigest()
        return cls.UA_HASH

    def _parse_line(self, line):
        if "#" in line:
            line, _ = line.split("#", 1)

        if ":" not in line:
            return None, None

        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()

        # https://github.com/google/robotstxt/blob/02bc6cdfa32db50d42563180c42aeb47042b4f0c/robots.cc#L690
        if key in ("dissallow", "dissalow", "disalow", "diasllow", "disallaw"):
            key = self.ROBOTS_TXT_DISALLOW

        if key in ("user_agent", "user agent", "useragent"):
            key = self.ROBOTS_TXT_USER_AGENT

        if key not in self.ROBOTS_TXT_KEYS:
            return None, None

        return key, val

    def _ua_matches(self, val):
        return val.lower() in user_agent().lower()

    def _parse_robotstxt(self, content):
        ua_rules = []
        generic_rules = []
        current_rules = None

        for line in content.splitlines():
            key, val = self._parse_line(line)

            if key is None:
                continue

            if key == self.ROBOTS_TXT_USER_AGENT:
                if self._ua_matches(val):
                    crawl_logger.debug(f"matching UA {val}")
                    current_rules = ua_rules
                elif val == "*":
                    crawl_logger.debug("global UA")
                    current_rules = generic_rules
                else:
                    current_rules = None
                continue

            if current_rules is None:
                continue

            val = re.escape(val)
            val = val.replace(r"\*", ".*")
            if val.endswith(r"\$"):
                val = val[:-2] + "$"

            current_rules.append((key, val))

        if ua_rules:
            rules = ua_rules
        elif generic_rules:
            rules = generic_rules
        else:
            rules = []

        self.robots_allow = "\n".join([val for key, val in rules if key == self.ROBOTS_TXT_ALLOW])
        self.robots_disallow = "\n".join([val for key, val in rules if key == self.ROBOTS_TXT_DISALLOW])

    def _load_robotstxt(self, url):
        from .browser_request import BrowserRequest

        self.robots_ua_hash = self.ua_hash()
        scheme, _ = url.split(":", 1)
        robots_url = f"{scheme}://{self.domain}/robots.txt"
        crawl_logger.debug(f"{self.domain}: downloading {robots_url}")

        try:
            page = BrowserRequest.get(robots_url, check_status=True)
            crawl_logger.debug(f"{self.domain}: loading {robots_url}")
            self._parse_robotstxt(page.content.decode("utf-8"))
        except (requests.HTTPError, TooManyRedirects):
            self.robots_status = DomainSetting.ROBOTS_EMPTY
        else:
            self.robots_status = DomainSetting.ROBOTS_LOADED
        crawl_logger.debug(f"{self.domain}: robots.txt {self.robots_status}")

    def robots_authorized(self, url):
        if self.ignore_robots:
            return True

        if self.robots_status == DomainSetting.ROBOTS_UNKNOWN or self.ua_hash() != self.robots_ua_hash:
            self._load_robotstxt(url)
            self.save()

        if self.robots_status == DomainSetting.ROBOTS_EMPTY:
            crawl_logger.debug(f"{self.domain}: robots.txt is empty")
            return True

        url = urlparse(url).path

        disallow_length = None
        for pattern in self.robots_disallow.split("\n"):
            if not pattern:
                continue
            if re.match(pattern, url):
                crawl_logger.debug(f"{url}: matched robots.txt disallow: {pattern}")
                disallow_length = max(disallow_length or 0, len(pattern))

        if disallow_length is None:
            crawl_logger.debug(f"{url}: robots.txt authorized")
            return True

        for pattern in self.robots_allow.split("\n"):
            if not pattern:
                continue
            if re.match(pattern, url):
                if len(pattern) > disallow_length:
                    crawl_logger.debug(f"{url}: robots.txt authorized by allow rule")
                    return True

        crawl_logger.debug(f"{url}: robots.txt denied")
        return False

    @classmethod
    def get_from_url(cls, url, default_browse_mode=None):
        from .crawl_policy import CrawlPolicy

        domain = urlparse(url).netloc

        if not default_browse_mode:
            crawl_policy = CrawlPolicy.get_from_url(url)
            default_browse_mode = crawl_policy.default_browse_mode

        return DomainSetting.objects.get_or_create(domain=domain, defaults={"browse_mode": default_browse_mode})[0]
