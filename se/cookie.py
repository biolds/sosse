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

import logging
from datetime import datetime
from http.cookiejar import Cookie as HttpJarCookie
from http.cookiejar import CookieJar
from urllib.parse import urlparse

import pytz
from django.db import models
from django.utils.timezone import now
from publicsuffix2 import PublicSuffixList, get_public_suffix

crawl_logger = logging.getLogger("crawler")


class Cookie(models.Model):
    TLDS = PublicSuffixList().tlds

    SAME_SITE_LAX = "Lax"
    SAME_SITE_STRICT = "Strict"
    SAME_SITE_NONE = "None"
    SAME_SITE = (
        (SAME_SITE_LAX, SAME_SITE_LAX),
        (SAME_SITE_STRICT, SAME_SITE_STRICT),
        (SAME_SITE_NONE, SAME_SITE_NONE),
    )
    domain = models.TextField(help_text="Domain name")
    domain_cc = models.TextField(help_text="Domain name attribute from the cookie", null=True, blank=True)
    inc_subdomain = models.BooleanField()
    name = models.TextField(blank=True)
    value = models.TextField(blank=True)
    path = models.TextField(default="/")
    expires = models.DateTimeField(null=True, blank=True)
    secure = models.BooleanField()
    same_site = models.CharField(max_length=6, choices=SAME_SITE, default=SAME_SITE_LAX)
    http_only = models.BooleanField(default=False)

    class Meta:
        unique_together = ("domain", "name", "path")

    def __str__(self):
        return f"{self.domain} - {self.name}"

    @classmethod
    def get_from_url(cls, url, queryset=None, expire=True):
        if not url.startswith("http:") and not url.startswith("https:"):
            return []

        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        url_path = parsed_url.path

        if queryset is None:
            queryset = Cookie.objects.all()

        if not url.startswith("https://"):
            queryset = queryset.filter(secure=False)

        _cookies = queryset.filter(domain=domain)

        V = models.Value
        F = models.F
        Concat = models.functions.Concat
        Right = models.functions.Right
        Len = models.functions.Length
        dom = ""

        for sub in domain.split("."):
            if dom != "":
                dom = "." + dom
            dom = sub + dom
            _cookies |= (
                queryset.filter(inc_subdomain=True)
                .annotate(
                    left=Right(V(domain), Len("domain") + 1),
                    right=Concat(V("."), "domain", output_field=models.TextField()),
                )
                .filter(left=F("right"))
            )

        cookies = []
        for c in _cookies:
            cookie_path = c.path.rstrip("/")
            if cookie_path == "" or url_path.rstrip("/") == cookie_path or url_path.startswith(cookie_path + "/"):
                if expire and c.expires and c.expires <= now():
                    c.delete()
                    continue
                cookies.append(c)

        return cookies

    @classmethod
    def set(cls, url: str | None, cookies: list[HttpJarCookie]):
        crawl_logger.debug(f"saving cookies for {url}: {cookies}")
        new_cookies = []
        set_cookies = [c["name"] for c in cookies]

        for c in cookies:
            name = c.pop("name")
            path = c.pop("path", "") or ""
            domain_cc = None

            cookie_dom = c.pop("domain", None)
            inc_subdomain = False

            if url:
                parsed_url = urlparse(url)
                domain = parsed_url.hostname
                if cookie_dom:
                    domain_cc = cookie_dom
                    cookie_dom = cookie_dom.lstrip(".")
                    inc_subdomain = True

                    if get_public_suffix(cookie_dom) != get_public_suffix(domain):
                        crawl_logger.warning(
                            f"{url} is trying to set a cookie ({name}) for a different domain {cookie_dom}"
                        )
                        continue

                    domain = cookie_dom
                if domain in cls.TLDS:
                    crawl_logger.warning(f"{url} is trying to set a cookie ({name}) for a TLD ({domain})")
                    continue
            else:
                domain = c.pop("domain_from_url").lstrip(".")
                inc_subdomain = c.pop("domain_specified")
                if inc_subdomain:
                    domain_cc = domain

            c["inc_subdomain"] = inc_subdomain
            c["domain"] = domain
            c["domain_cc"] = domain_cc

            if not c.get("same_site"):
                c["same_site"] = Cookie._meta.get_field("same_site").default
            cookie, created = Cookie.objects.update_or_create(domain=domain, path=path, name=name, defaults=c)

            if created:
                new_cookies.append(cookie)

        if url:
            # delete missing cookies
            current = cls.get_from_url(url)
            for c in current:
                if c.name not in set_cookies:
                    crawl_logger.debug(f"{c.name} not in {set_cookies}")
                    c.delete()
        return new_cookies

    @classmethod
    def set_from_jar(cls, url: str | None, cookie_jar: CookieJar):
        _cookies = []

        for cookie in cookie_jar:
            expires = cookie.expires
            if expires:
                expires = datetime.fromtimestamp(expires, pytz.utc)

            c = {
                "domain": cookie.get_nonstandard_attr("Domain"),
                "name": cookie.name,
                "value": cookie.value,
                "path": cookie.path,
                "expires": expires,
                "secure": cookie.secure,
                "same_site": cookie.get_nonstandard_attr("SameSite"),
                # Requests has "HttpOnly", while loading from FileCookieJar has HTTPOnly"
                "http_only": cookie.has_nonstandard_attr("HttpOnly") or cookie.has_nonstandard_attr("HTTPOnly"),
            }
            if url is None:
                c["domain_from_url"] = cookie.domain
                c["domain_specified"] = cookie.domain_specified

            _cookies.append(c)

        cls.set(url, _cookies)
