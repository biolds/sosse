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
from .domain import Domain
from .tag import Tag
from .utils import build_multiline_re
from .webhook import Webhook

crawl_logger = logging.getLogger("crawler")
BROWSER_MAP = {
    Domain.BROWSE_CHROMIUM: BrowserChromium,
    Domain.BROWSE_FIREFOX: BrowserFirefox,
    Domain.BROWSE_REQUESTS: BrowserRequest,
}


@transaction.atomic
def validate_url_regexp(val):
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


class Collection(models.Model):
    RECRAWL_FREQ_NONE = "none"
    RECRAWL_FREQ_CONSTANT = "constant"
    RECRAWL_FREQ_ADAPTIVE = "adaptive"
    RECRAWL_FREQ = [
        (RECRAWL_FREQ_NONE, "Once"),
        (RECRAWL_FREQ_CONSTANT, "Constant time"),
        (RECRAWL_FREQ_ADAPTIVE, "Adaptive"),
    ]

    HASH_RAW = "raw"
    HASH_NO_NUMBERS = "no_numbers"
    HASH_MODE = [
        (HASH_RAW, "Raw content"),
        (HASH_NO_NUMBERS, "Normalize numbers"),
    ]

    RECRAWL_COND_ON_CHANGE = "change"
    RECRAWL_COND_ALWAYS = "always"
    RECRAWL_COND_MANUAL = "manual"
    RECRAWL_CONDITION = [
        (RECRAWL_COND_ON_CHANGE, "On change only"),
        (RECRAWL_COND_ALWAYS, "Always"),
        (RECRAWL_COND_MANUAL, "On change or manual trigger"),
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

    name = models.CharField(max_length=256, unique=True)
    unlimited_regex = models.TextField(
        blank=True,
        default="",
        validators=[validate_url_regexp],
        verbose_name="Unlimited depth URL regex",
        help_text="URL regular expressions. Matching URLs will have unlimited crawling recursion depth (one per line; lines starting with # are ignored)",
    )
    unlimited_regex_pg = models.TextField(default="")
    limited_regex = models.TextField(
        blank=True,
        default="",
        validators=[validate_url_regexp],
        verbose_name="Limited depth URL regex",
        help_text="URL regular expressions. Matching URLs will have limited crawling recursion depth (one per line; lines starting with # are ignored)",
    )
    limited_regex_pg = models.TextField(default="")
    combined_regex_pg = models.TextField(default="")
    excluded_regex = models.TextField(
        blank=True,
        default="",
        validators=[validate_url_regexp],
        verbose_name="Excluded URL regex",
        help_text="URL regular expressions to exclude from this collection. (one by line, lines starting with # are ignored)",
    )
    excluded_regex_pg = models.TextField(default="")
    mimetype_regex = models.TextField(default=".*")
    recursion_depth = models.PositiveIntegerField(
        default=1,
        verbose_name="Limited recursion depth",
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
        choices=Domain.BROWSE_MODE,
        default=Domain.BROWSE_DETECT,
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
        help_text="Javascript code to execute after the page is loaded. If an object is returned, its content will be "
        "used to overwrite the document's fields",
        blank=True,
    )
    store_extern_links = models.BooleanField(default=False, help_text="Store links to non-indexed pages")

    recrawl_freq = models.CharField(
        max_length=8,
        choices=RECRAWL_FREQ,
        default=RECRAWL_FREQ_ADAPTIVE,
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
        verbose_name="Change detection",
        help_text="Content to check for modifications",
    )
    recrawl_condition = models.CharField(
        max_length=10,
        choices=RECRAWL_CONDITION,
        default=RECRAWL_COND_MANUAL,
        verbose_name="Condition",
        help_text="Specifies the conditions under which a page is reprocessed",
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
    tags = models.ManyToManyField(Tag, blank=True)
    webhooks = models.ManyToManyField(Webhook)

    # Cross-collection crawl settings
    queue_to_any_collection = models.BooleanField(
        default=False,
        verbose_name="Queue links to any collection",
        help_text="When a URL doesn't match this Collection's regex patterns, check all Collections and queue it in the first matching one.",
    )
    queue_to_collections = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        verbose_name="Queue links to specific collections",
        help_text="When a URL doesn't match this Collection's regex patterns, check only these Collections and queue it there.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.unlimited_regex_pg = build_multiline_re(self.unlimited_regex) if self.unlimited_regex else ""
        self.limited_regex_pg = build_multiline_re(self.limited_regex) if self.limited_regex else ""
        self.excluded_regex_pg = build_multiline_re(self.excluded_regex) if self.excluded_regex else ""

        # Build combined regex for cross-collection matching
        if self.unlimited_regex_pg and self.limited_regex_pg:
            self.combined_regex_pg = f"{self.unlimited_regex_pg}|{self.limited_regex_pg}"
        elif self.unlimited_regex_pg:
            self.combined_regex_pg = self.unlimited_regex_pg
        elif self.limited_regex_pg:
            self.combined_regex_pg = self.limited_regex_pg
        else:
            self.combined_regex_pg = ""

        return super().save(*args, **kwargs)

    @staticmethod
    def create_default():
        try:
            return Collection.objects.get(name="Default")
        except Collection.DoesNotExist:
            existing = Collection.objects.first()
            if existing:
                return existing
            return Collection.objects.create(name="Default")

    @staticmethod
    def get_from_url(url, collections_to_check=None):
        collections = (
            Collection.objects.annotate(
                match_len=models.functions.Length(
                    models.Func(
                        models.Value(url),
                        models.F("combined_regex_pg"),
                        function="REGEXP_SUBSTR",
                        output_field=models.TextField(),
                    )
                )
            )
            .filter(match_len__gt=0)
            .order_by("-match_len")
        )

        # If specific collections are provided, filter to only those
        if collections_to_check is not None:
            collections_to_check_ids = {c.pk for c in collections_to_check}

        for collection in collections:
            # If we have a filter list, check if this collection is in it
            if collections_to_check is not None and collection.pk not in collections_to_check_ids:
                continue

            if not collection.combined_regex_pg:
                continue

            if Document._url_matches_regex(url, collection.excluded_regex_pg):
                continue
            return collection

        return None

    @staticmethod
    def _default_browser():
        if settings.SOSSE_DEFAULT_BROWSER == "chromium":
            return Domain.BROWSE_CHROMIUM
        return Domain.BROWSE_FIREFOX

    def url_get(self, url, domain=None):
        domain = domain or Domain.get_from_url(url)
        browser = self.get_browser(domain=domain, no_detection=False)
        page = browser.get(url, self)

        if page.redirect_count:
            # The request was redirected, check if we need auth
            try:
                crawl_logger.debug(f"may auth {page.url} / {self.auth_login_url_re}")
                if self.auth_login_url_re and self.auth_form_selector and re.search(self.auth_login_url_re, page.url):
                    crawl_logger.debug(f"doing auth for {url}")
                    new_page = page.browser.try_auth(page, url, self)

                    if new_page.url != url:
                        crawl_logger.debug(f"reopening {url} after auth")
                        page = browser.get(url, self)
                    else:
                        page = new_page
            except Exception as e:
                if isinstance(e, AuthElemFailed):
                    raise
                raise Exception("Authentication failed")

        if self.default_browse_mode == Domain.BROWSE_DETECT and domain.browse_mode == Domain.BROWSE_DETECT:
            crawl_logger.debug(f"browser detection on {url}")
            requests_page = BrowserRequest.get(url, self)
            browser_content = page.dom_walk(self, False, None)
            requests_content = requests_page.dom_walk(self, False, None)

            if browser_content["text"] != requests_content["text"]:
                new_mode = self._default_browser()
            else:
                new_mode = Domain.BROWSE_REQUESTS
                page = requests_page
            crawl_logger.debug(f"browser detected {new_mode} on {url}")
            domain.browse_mode = new_mode
            domain.save()
        return page

    def get_browser(self, url=None, domain=None, no_detection=True):
        if url is None and domain is None:
            raise Exception("Either url or domain must be provided")
        if url is not None and domain is not None:
            raise Exception("Either url or domain must be provided")

        if url:
            domain = Domain.get_from_url(url)

        browser_str = self.default_browse_mode
        if self.default_browse_mode == Domain.BROWSE_DETECT:
            if domain.browse_mode == Domain.BROWSE_DETECT:
                if no_detection:
                    raise Exception(f"browser mode is not yet known ({domain})")
                browser_str = self._default_browser()
            else:
                browser_str = domain.browse_mode

        return BROWSER_MAP[browser_str]
