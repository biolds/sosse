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

import requests
import urllib3.util.url
from django.conf import settings
from requests.adapters import HTTPAdapter

from .browser import AuthElemFailed, Browser, PageTooBig, TooManyRedirects
from .browser_request_hack import _encode_invalid_chars
from .cookie import Cookie
from .domain import user_agent
from .page import Page
from .url import absolutize_url, url_remove_fragment

urllib3.util.url._encode_invalid_chars = _encode_invalid_chars
crawl_logger = logging.getLogger("crawler")


def dict_merge(a, b):
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            dict_merge(a[key], b[key])
        else:
            a[key] = b[key]
    return a


def requests_params(_params):
    params = {}

    if settings.SOSSE_PROXY:
        params["proxies"] = {
            "http": settings.SOSSE_PROXY,
            "https": settings.SOSSE_PROXY,
        }
    if settings.SOSSE_REQUESTS_TIMEOUT:
        params["timeout"] = settings.SOSSE_REQUESTS_TIMEOUT
    return dict_merge(params, _params)


class BrowserRequest(Browser):
    @classmethod
    def _init(cls):
        pass

    @classmethod
    def _destroy(cls):
        pass

    @classmethod
    def _page_from_request(cls, r):
        content = r._content
        page = Page(r.url, content, cls, r.headers, r.status_code)

        soup = page.get_soup()
        if soup:
            page.title = soup.title and soup.title.string
        return page

    @classmethod
    def _get_cookies(cls, url):
        jar = requests.cookies.RequestsCookieJar()

        for c in Cookie.get_from_url(url):
            expires = None
            if c.expires:
                expires = int(c.expires.strftime("%s"))

            rest = {"SameSite": c.same_site}
            if c.http_only:
                rest["HttpOnly"] = (c.http_only,)
            jar.set(
                c.name,
                c.value,
                path=c.path,
                domain=c.domain,
                expires=expires,
                secure=c.secure,
                rest=rest,
            )
        crawl_logger.debug(f"loading cookies for {url}: {jar}")
        return jar

    @classmethod
    def _requests_params(cls):
        return requests_params(
            {
                "allow_redirects": False,
                "stream": True,
                "headers": {
                    "User-Agent": user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                },
            }
        )

    _session_cache = {}

    @classmethod
    def _get_session(cls, url):
        """Get or create a cached session for the given hostname."""
        hostname = requests.utils.urlparse(url).hostname
        if hostname not in cls._session_cache:
            session = requests.Session()
            adapter = HTTPAdapter(max_retries=0)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            cls._session_cache[hostname] = session
        return cls._session_cache[hostname]

    @classmethod
    def _requests_query(cls, method, url, max_file_size, **kwargs):
        jar = cls._get_cookies(url)
        crawl_logger.debug(f"from the jar: {jar}")

        session = cls._get_session(url)
        session.cookies = jar

        func = getattr(session, method)
        kwargs = dict_merge(cls._requests_params(), kwargs)

        # Drop the referer if the request is cross-origin
        if kwargs.get("headers", {}).get("Referer"):
            parsed_url = requests.utils.urlparse(url)
            referer_parsed = requests.utils.urlparse(kwargs["headers"]["Referer"])
            if parsed_url.hostname != referer_parsed.hostname:
                kwargs["headers"].pop("Referer")

        r = func(url, **kwargs)
        Cookie.set_from_jar(url, session.cookies)

        content_length = int(r.headers.get("content-length", 0))
        if content_length / 1024 > max_file_size:
            r.close()
            raise PageTooBig(content_length, max_file_size)

        content = b""
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            content += chunk
            if len(content) / 1024 >= max_file_size:
                break
        r.close()

        if len(content) / 1024 > max_file_size:
            raise PageTooBig(len(content), max_file_size)

        r._content = content
        crawl_logger.debug(f"after request jar: {session.cookies}")
        return r

    @classmethod
    def get(
        cls,
        url,
        collection,
        check_status=False,
        max_file_size=None,
        **kwargs,
    ) -> Page:
        from .collection import Collection

        REDIRECT_CODE = (301, 302, 307, 308)
        page = None
        redirect_count = 0

        if collection is not None and not isinstance(collection, Collection):
            raise Exception("Collection must be None or an instance of Collection")

        if max_file_size is None:
            # max_file_size cannot be set as a kwargs paramater, as it prevents
            # to override the value of settings.SOSSE_MAX_FILE_SIZE with override_settings
            max_file_size = settings.SOSSE_MAX_FILE_SIZE

        while redirect_count <= settings.SOSSE_MAX_REDIRECTS:
            r = cls._requests_query("get", url, max_file_size, **kwargs)

            if check_status:
                r.raise_for_status()

            if r.status_code in REDIRECT_CODE:
                crawl_logger.debug(f"{url}: redirected")
                redirect_count += 1
                dest = r.headers.get("location")
                url = absolutize_url(url, dest)
                url = url_remove_fragment(url)
                crawl_logger.debug(f"got redirected to {url}")
                if not url:
                    raise Exception(f"Got a {r.status_code} code without a location header")

                continue

            page = cls._page_from_request(r)

            # Check for an HTML / meta redirect
            soup = page.get_soup()
            if soup:
                has_redirect = False
                for meta in page.get_soup().find_all("meta"):
                    if meta.get("http-equiv", "").lower() == "refresh" and meta.get("content", ""):
                        # handle redirect
                        dest = meta.get("content")

                        if ";" in dest:
                            dest = dest.split(";", 1)[1]

                        if dest.startswith("url="):
                            dest = dest[4:]

                            url = absolutize_url(url, dest)
                            url = url_remove_fragment(url)
                            redirect_count += 1
                            has_redirect = True
                            crawl_logger.debug(f"{url}: html redirected {meta}")
                            break
                if has_redirect:
                    continue
            break

        if redirect_count > settings.SOSSE_MAX_REDIRECTS:
            raise TooManyRedirects()

        page.redirect_count = redirect_count
        return page

    @classmethod
    def try_auth(cls, page, url, collection):
        parsed = page.get_soup()
        form = parsed.select(collection.auth_form_selector)

        if len(form) == 0:
            raise AuthElemFailed(
                page,
                f"Could not find element with CSS selector: {collection.auth_form_selector}",
            )

        if len(form) > 1:
            raise AuthElemFailed(
                page,
                f"Found multiple element with CSS selector: {collection.auth_form_selector}",
            )

        form = form[0]
        payload = {}
        for elem in form.find_all("input"):
            if elem.get("name"):
                payload[elem.get("name")] = elem.get("value")

        for f in collection.authfield_set.values("key", "value"):
            payload[f["key"]] = f["value"]

        post_url = form.get("action")
        if post_url:
            post_url = absolutize_url(page.url, post_url)
            post_url = url_remove_fragment(post_url)
        else:
            post_url = page.url

        crawl_logger.debug(f"authenticating to {post_url} with {payload}")
        r = cls._requests_query("post", post_url, settings.SOSSE_MAX_FILE_SIZE, data=payload)
        if r.status_code != 302:
            crawl_logger.debug("no redirect after auth")
            return cls._page_from_request(r)

        location = r.headers.get("location")
        if not location:
            raise Exception("No location in the redirection")

        location = absolutize_url(r.url, location)
        location = url_remove_fragment(location)
        crawl_logger.debug(f"got redirected to {location} after authentication")
        return cls.get(location, collection)
