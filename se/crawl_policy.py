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
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DataError, connection, models, transaction

from .browser import AuthElemFailed
from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .browser_request import BrowserRequest
from .document import Document
from .domain_setting import DomainSetting
from .utils import plural

crawl_logger = logging.getLogger("crawler")
BROWSER_MAP = {
    DomainSetting.BROWSE_CHROMIUM: BrowserChromium,
    DomainSetting.BROWSE_FIREFOX: BrowserFirefox,
    DomainSetting.BROWSE_REQUESTS: BrowserRequest,
}


@transaction.atomic
def validate_url_regexp(val):
    if val == "(default)":
        raise ValidationError('"(default)" policy is reserved')
    cursor = connection.cursor()
    for line_no, line in enumerate(val.splitlines()):
        line = line.strip()
        if line.startswith("#") or not line:
            continue

        try:
            # Try the regexp on Psql
            cursor.execute("SELECT 1 FROM se_document WHERE url ~ %s", params=[val])
        except DataError as e:
            if len(val.splitlines()) == 1:
                error = e.__cause__
            else:
                error = f"Regex on line {line_no + 1} failed: {e.__cause__}"
            raise ValidationError(error)


class CrawlPolicy(models.Model):
    RECRAWL_NONE = "none"
    RECRAWL_CONSTANT = "constant"
    RECRAWL_ADAPTIVE = "adaptive"
    RECRAWL_MODE = [
        (RECRAWL_NONE, "Once"),
        (RECRAWL_CONSTANT, "Constant time"),
        (RECRAWL_ADAPTIVE, "Adaptive"),
    ]

    HASH_RAW = "raw"
    HASH_NO_NUMBERS = "no_numbers"
    HASH_MODE = [
        (HASH_RAW, "Hash raw content"),
        (HASH_NO_NUMBERS, "Normalize numbers before"),
    ]

    CRAWL_ALL = "always"
    CRAWL_ON_DEPTH = "depth"
    CRAWL_NEVER = "never"
    CRAWL_CONDITION = [
        (CRAWL_ALL, "Crawl all pages"),
        (CRAWL_ON_DEPTH, "Depending on depth"),
        (CRAWL_NEVER, "Never crawl"),
    ]

    REMOVE_NAV_FROM_INDEX = "idx"
    REMOVE_NAV_FROM_SCREENSHOT = "scr"
    REMOVE_NAV_FROM_ALL = "yes"
    REMOVE_NAV_NO = "no"
    REMOVE_NAV = [
        (REMOVE_NAV_FROM_INDEX, "From index"),
        (REMOVE_NAV_FROM_SCREENSHOT, "From index and screenshots"),
        (REMOVE_NAV_FROM_ALL, "From index, screens and HTML snaps"),
        (REMOVE_NAV_NO, "No"),
    ]

    THUMBNAIL_MODE_PREVIEW = "preview"
    THUMBNAIL_MODE_PREV_OR_SCREEN = "prevscreen"
    THUMBNAIL_MODE_SCREENSHOT = "screenshot"
    THUMBNAIL_MODE_NONE = "none"
    THUMBNAIL_MODE = (
        (THUMBNAIL_MODE_PREVIEW, "Page preview from metadata"),
        (THUMBNAIL_MODE_PREV_OR_SCREEN, "Preview from meta, screenshot as fallback"),
        (THUMBNAIL_MODE_SCREENSHOT, "Take a screenshot"),
        (THUMBNAIL_MODE_NONE, "No thumbnail"),
    )
    url_regex = models.TextField(
        validators=[validate_url_regexp],
        help_text="URL regular expressions for this policy. (one by line, lines starting with # are ignored)",
    )
    url_regex_pg = models.TextField()
    enabled = models.BooleanField(default=True)
    recursion = models.CharField(max_length=6, choices=CRAWL_CONDITION, default=CRAWL_ALL)
    mimetype_regex = models.TextField(default=".*")
    recursion_depth = models.PositiveIntegerField(
        default=0,
        help_text="Level of external links (links that don't match the regex) to recurse into",
    )
    keep_params = models.BooleanField(
        default=True,
        verbose_name="Index URL parameters",
        help_text='When disabled, URL parameters (parameters after "?") are removed from URLs, this can be useful if some parameters are random, change sorting or filtering, ...',
    )
    hide_documents = models.BooleanField(default=False, help_text="Hide documents from search results")

    default_browse_mode = models.CharField(
        max_length=8,
        choices=DomainSetting.BROWSE_MODE,
        default=DomainSetting.BROWSE_DETECT,
        help_text="Python Request is faster, but can't execute Javascript and may break pages",
    )

    snapshot_html = models.BooleanField(
        default=True,
        help_text="Archive binary files, HTML content and download related assets",
        verbose_name="Archive content 🔖",
    )
    snapshot_exclude_url_re = models.TextField(
        blank=True,
        default="",
        help_text="Regex of URL to skip related assets downloading",
        verbose_name="Assets exclude URL regex",
    )
    snapshot_exclude_mime_re = models.TextField(
        blank=True,
        default="",
        help_text="Regex of mimetypes to skip related assets saving",
        verbose_name="Assets exclude mime regex",
    )
    snapshot_exclude_element_re = models.TextField(
        blank=True,
        default="",
        help_text="Regex of HTML elements to skip related assets downloading",
        verbose_name="Assets exclude HTML regex",
    )

    thumbnail_mode = models.CharField(
        default=THUMBNAIL_MODE_PREVIEW,
        help_text="Save thumbnails to display in search results",
        choices=THUMBNAIL_MODE,
        max_length=10,
    )
    take_screenshots = models.BooleanField(
        default=False,
        help_text="Store pages as screenshots",
        verbose_name="Take screenshots 📷",
    )
    screenshot_format = models.CharField(
        max_length=3,
        choices=Document.SCREENSHOT_FORMAT,
        default=Document.SCREENSHOT_JPG,
    )

    remove_nav_elements = models.CharField(
        default=REMOVE_NAV_FROM_INDEX,
        help_text="Remove navigation related elements",
        choices=REMOVE_NAV,
        max_length=4,
    )
    script = models.TextField(
        default="",
        help_text="Javascript code to execute after the page is loaded",
        blank=True,
    )
    store_extern_links = models.BooleanField(default=False, help_text="Store links to non-indexed pages")

    recrawl_mode = models.CharField(
        max_length=8,
        choices=RECRAWL_MODE,
        default=RECRAWL_ADAPTIVE,
        verbose_name="Crawl frequency",
        help_text="Adaptive frequency will increase delay between two crawls when the page stays unchanged",
    )
    recrawl_dt_min = models.DurationField(
        blank=True,
        null=True,
        help_text="Min. time before recrawling a page",
        default=timedelta(days=1),
    )
    recrawl_dt_max = models.DurationField(
        blank=True,
        null=True,
        help_text="Max. time before recrawling a page",
        default=timedelta(days=365),
    )
    hash_mode = models.CharField(
        max_length=10,
        choices=HASH_MODE,
        default=HASH_NO_NUMBERS,
        help_text="Page content hashing method used to detect changes in the content",
    )

    auth_login_url_re = models.TextField(
        null=True,
        blank=True,
        verbose_name="Login URL regex",
        help_text="A redirection to an URL matching the regex will trigger authentication",
    )
    auth_form_selector = models.TextField(
        null=True,
        blank=True,
        verbose_name="Form selector",
        help_text="CSS selector pointing to the authentication &lt;form&gt; element",
    )

    class Meta:
        verbose_name_plural = "crawl policies"

    def __str__(self):
        if self.url_regex:
            url_regexs = [line.strip() for line in self.url_regex.splitlines()]
            url_regexs = [line for line in url_regexs if not line.startswith("#") and line]
            if len(url_regexs) == 1:
                return f"「{url_regexs[0]}」"
            elif len(url_regexs) > 1:
                others = len(url_regexs) - 1
                others = f"{others} other{plural(others)}"
                return f"「{url_regexs[0]} (and {others})」"
        return "「<empty>」"

    def save(self, *args, **kwargs):
        if self.url_regex == "(default)":
            self.url_regex_pg = ".*"
            self.enabled = True
        else:
            url_regexs = [line.strip() for line in self.url_regex.splitlines()]
            url_regexs = [line for line in url_regexs if not line.startswith("#") and line]
            match len(url_regexs):
                case 0:
                    self.url_regex_pg = ""
                case 1:
                    self.url_regex_pg = url_regexs[0]
                case _:
                    self.url_regex_pg = "(" + "|".join(url_regexs) + ")"
        return super().save(*args, **kwargs)

    @staticmethod
    def create_default():
        # mandatory default policy
        policy, _ = CrawlPolicy.objects.get_or_create(
            url_regex="(default)", defaults={"url_regex_pg": ".*", "recursion": CrawlPolicy.CRAWL_NEVER}
        )
        return policy

    @staticmethod
    def get_from_url(url, queryset=None):
        if queryset is None:
            queryset = CrawlPolicy.objects.all()
        queryset = queryset.filter(enabled=True)
        queryset = queryset.exclude(url_regex="(default)")
        queryset = queryset.exclude(url_regex_pg="")

        policy = (
            queryset.annotate(
                match_len=models.functions.Length(
                    models.Func(
                        models.Value(url),
                        models.F("url_regex_pg"),
                        function="REGEXP_SUBSTR",
                        output_field=models.TextField(),
                    )
                )
            )
            .filter(match_len__gt=0)
            .order_by("-match_len")
            .first()
        )

        if policy is None:
            return CrawlPolicy.create_default()

        return policy

    @staticmethod
    def _default_browser():
        if settings.SOSSE_DEFAULT_BROWSER == "chromium":
            return DomainSetting.BROWSE_CHROMIUM
        return DomainSetting.BROWSE_FIREFOX

    def url_get(self, url, domain_setting=None):
        domain_setting = domain_setting or DomainSetting.get_from_url(url, self.default_browse_mode)
        browser = self.get_browser(domain_setting=domain_setting, no_detection=False)
        page = browser.get(url)

        if page.redirect_count:
            # The request was redirected, check if we need auth
            try:
                crawl_logger.debug(f"may auth {page.url} / {self.auth_login_url_re}")
                if self.auth_login_url_re and self.auth_form_selector and re.search(self.auth_login_url_re, page.url):
                    crawl_logger.debug(f"doing auth for {url}")
                    new_page = page.browser.try_auth(page, url, self)

                    if new_page.url != url:
                        crawl_logger.debug(f"reopening {url} after auth")
                        page = browser.get(url)
                    else:
                        page = new_page
            except Exception as e:
                if isinstance(e, AuthElemFailed):
                    raise
                raise Exception("Authentication failed")

        if domain_setting.browse_mode == DomainSetting.BROWSE_DETECT:
            crawl_logger.debug(f"browser detection on {url}")
            requests_page = BrowserRequest.get(url)
            browser_content = page.dom_walk(self, False, None)
            requests_content = requests_page.dom_walk(self, False, None)

            if browser_content["text"] != requests_content["text"]:
                new_mode = self._default_browser()
            else:
                new_mode = DomainSetting.BROWSE_REQUESTS
                page = requests_page
            crawl_logger.debug(f"browser detected {new_mode} on {url}")
            domain_setting.browse_mode = new_mode
            domain_setting.save()
        return page

    def get_browser(self, url=None, domain_setting=None, no_detection=True):
        if url is None and domain_setting is None:
            raise Exception("Either url or domain_setting must be provided")
        if url is not None and domain_setting is not None:
            raise Exception("Either url or domain_setting must be provided")

        if url:
            domain_setting = DomainSetting.get_from_url(url, self.default_browse_mode)

        browser_str = self.default_browse_mode
        if self.default_browse_mode == DomainSetting.BROWSE_DETECT:
            if domain_setting.browse_mode == DomainSetting.BROWSE_DETECT:
                if no_detection:
                    raise Exception(f"browser mode is not yet known ({domain_setting})")
                browser_str = self._default_browser()
            else:
                browser_str = domain_setting.browse_mode

        return BROWSER_MAP[browser_str]
