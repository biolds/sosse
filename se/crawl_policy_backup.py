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

from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models

from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .browser_request import BrowserRequest
from .document import Document
from .domain import Domain

BROWSER_MAP = {
    Domain.BROWSE_CHROMIUM: BrowserChromium,
    Domain.BROWSE_FIREFOX: BrowserFirefox,
    Domain.BROWSE_REQUESTS: BrowserRequest,
}


class CrawlPolicyBackup(models.Model):
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
    tags = ArrayField(
        models.CharField(max_length=128),
        blank=True,
        default=list,
    )
    webhooks = ArrayField(
        models.CharField(max_length=512),
        blank=True,
        default=list,
    )


class AuthFieldBackup(models.Model):
    key = models.CharField(max_length=256, verbose_name="<input> name attribute")
    value = models.CharField(max_length=256)
    crawl_policy = models.ForeignKey("CrawlPolicyBackup", on_delete=models.CASCADE)
