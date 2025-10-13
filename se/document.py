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
import os
import re
import unicodedata
from datetime import datetime
from hashlib import md5
from time import mktime, sleep
from traceback import format_exc

import feedparser
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import connection, models
from django.template.loader import get_template
from django.utils.html import format_html
from django.utils.timezone import now
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from PIL import Image

from .browser import AuthElemFailed, SkipIndexing
from .document_meta import DocumentMeta
from .domain import Domain
from .html_cache import HTMLAsset, HTMLCache
from .html_snapshot import HTMLSnapshot
from .mime_plugin import MimePlugin
from .tag import Tag
from .url import url_beautify, validate_url
from .utils import reverse_no_escape
from .webhook import Webhook

crawl_logger = logging.getLogger("crawler")

DetectorFactory.seed = 0


def example_doc():
    return Document(
        url="https://example.com/",
        title="Example Title",
        mimetype="text/html",
        lang_iso_639_1="en",
        content="Example",
    )


def remove_accent(s):
    # append an ascii version to match on non-accented letters
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


class RegConfigField(models.Field):
    def db_type(self, connection):
        return "regconfig"


def extern_link_flags():
    opt = ""
    if settings.SOSSE_LINKS_NO_REFERRER:
        opt += ' rel="noreferrer"'
    if settings.SOSSE_LINKS_NEW_TAB:
        opt += ' target="_blank"'
    return format_html(opt)


class DocumentManager(models.Manager):
    def count(self):
        return super().get_queryset().count()

    def none(self):
        return super().get_queryset().none()

    def create(self, *args, **kwargs):
        return super().get_queryset().create(*args, **kwargs)

    def update(self, *args, **kwargs):
        return super().get_queryset().update(*args, **kwargs)

    def w_content(self):
        return super().get_queryset()

    def wo_content(self):
        return super().get_queryset().defer("content", "normalized_content", "vector", "error")

    def get_queryset(self):
        raise Exception("Use w_content() or wo_content()")


class Document(models.Model):
    SCREENSHOT_PNG = "png"
    SCREENSHOT_JPG = "jpg"
    SCREENSHOT_FORMAT = (
        (SCREENSHOT_PNG, SCREENSHOT_PNG),
        (SCREENSHOT_JPG, SCREENSHOT_JPG),
    )
    DISPLAY_QUEUE_SIZE = 10

    # Document info
    url = models.TextField(validators=[validate_url])
    collection = models.ForeignKey("se.Collection", on_delete=models.CASCADE)

    normalized_url = models.TextField()
    title = models.TextField()
    normalized_title = models.TextField()
    content = models.TextField()
    normalized_content = models.TextField()
    content_hash = models.TextField(null=True, blank=True)
    vector = SearchVectorField(null=True, blank=True)
    lang_iso_639_1 = models.CharField(max_length=6, null=True, blank=True, verbose_name="Language")
    vector_lang = RegConfigField(default="simple")
    mimetype = models.CharField(max_length=128, null=True, blank=True)
    hidden = models.BooleanField(default=False, help_text="Hide this document from search results")
    retries = models.PositiveIntegerField(default=0, verbose_name="Crawl retries")

    favicon = models.ForeignKey("FavIcon", null=True, blank=True, on_delete=models.SET_NULL)
    robotstxt_rejected = models.BooleanField(default=False, verbose_name="Rejected by robots.txt")
    has_html_snapshot = models.BooleanField(default=False)

    # HTTP status
    redirect_url = models.TextField(null=True, blank=True)
    too_many_redirects = models.BooleanField(default=False)

    screenshot_count = models.PositiveIntegerField(default=0)
    screenshot_format = models.CharField(max_length=3, choices=SCREENSHOT_FORMAT)
    screenshot_size = models.CharField(max_length=16)

    has_thumbnail = models.BooleanField(default=False)

    # Crawling info
    crawl_first = models.DateTimeField(blank=True, null=True, verbose_name="Crawled first")
    crawl_last = models.DateTimeField(blank=True, null=True, verbose_name="Crawled last")
    crawl_next = models.DateTimeField(blank=True, null=True, verbose_name="Crawl next")
    crawl_dt = models.DurationField(blank=True, null=True, verbose_name="Crawl DT")
    crawl_recurse = models.PositiveIntegerField(default=0, verbose_name="Recursion remaining")
    modified_date = models.DateTimeField(blank=True, null=True, verbose_name="Last modification date")
    manual_crawl = models.BooleanField(default=False)

    error = models.TextField(blank=True, default="")
    error_hash = models.TextField(blank=True, default="")
    show_on_homepage = models.BooleanField(default=False, help_text="Display this document on the homepage")

    worker_no = models.PositiveIntegerField(blank=True, null=True)
    webhooks_result = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    mime_plugins_result = models.TextField(blank=True, default="")

    tags = models.ManyToManyField(Tag, blank=True)

    supported_langs = None

    objects = DocumentManager()

    class Meta:
        unique_together = ("url", "collection")
        indexes = [
            GinIndex(fields=(("vector",))),
            # models.Index(models.F('show_on_homepage') == models.Value(True),
            #             models.F('title').asc(), name='home_idx')
            # Indexes for crawl scheduling
            models.Index(fields=["worker_no"]),
            models.Index(fields=["crawl_last"]),
            models.Index(fields=["crawl_next"]),
            models.Index(fields=["worker_no", "crawl_last", "crawl_next", "id"]),
            # Index for new collection field
            models.Index(fields=["collection"]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_name = None

    def __str__(self):
        return self.url

    def get_absolute_url(self):
        # Construct URL with collection prefix
        url_arg = f"{self.collection.id}/{self.url}"

        if self.screenshot_count or self.redirect_url:
            return reverse_no_escape("screenshot", args=(url_arg,))

        if self.has_html_snapshot:
            asset = HTMLAsset.objects.filter(url=self.url).first()
            if asset and os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
                if self.mimetype.startswith("text/"):
                    return reverse_no_escape("html", args=(url_arg,))
                else:
                    return reverse_no_escape("download", args=(url_arg,))

        if self.content:
            return reverse_no_escape("www", args=(url_arg,))
        return reverse_no_escape("words", args=(url_arg,))

    def get_source_link(self):
        link = '🌍&nbsp<a href="{}"'
        link += extern_link_flags()
        link += ">Source</a>"
        return format_html(link, self.url)

    def get_title_label(self):
        if self.redirect_url:
            return f"<Redirect to {self.redirect_url}>"
        return self.title or self.url

    def image_name(self):
        if not self._image_name:
            filename = md5(self.url.encode("utf-8"), usedforsecurity=False).hexdigest()
            base_dir = filename[:2]
            self._image_name = os.path.join(base_dir, filename)
        return self._image_name

    @classmethod
    def get_supported_langs(cls):
        if cls.supported_langs is not None:
            return cls.supported_langs

        with connection.cursor() as cursor:
            cursor.execute("SELECT cfgname FROM pg_catalog.pg_ts_config WHERE cfgname != 'simple'")
            row = cursor.fetchall()

        cls.supported_langs = [r[0] for r in row]
        return cls.supported_langs

    @classmethod
    def get_supported_lang_dict(cls):
        supported = cls.get_supported_langs()
        langs = {}
        for iso, lang in settings.SOSSE_LANGDETECT_TO_POSTGRES.items():
            if lang["name"] in supported:
                langs[iso] = lang
        return langs

    @classmethod
    def _get_lang(cls, text):
        try:
            lang_iso = detect(text)
        except LangDetectException:
            lang_iso = None

        lang_pg = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get("name")
        if lang_pg not in cls.get_supported_langs():
            lang_pg = settings.SOSSE_FAIL_OVER_LANG

        return lang_iso, lang_pg

    def lang_flag(self, full=False):
        lang = self.lang_iso_639_1
        flag = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang, {}).get("flag")

        if full:
            lang = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang, {}).get("name", lang)
        if flag:
            lang = f"{flag} {lang}"

        return lang

    def _hash_content(self, content):
        if not self.mimetype:
            raise Exception("mimetype is required")

        if self.mimetype.startswith("text/"):
            if not isinstance(content, str):
                raise ValueError("content must be a string")

            from .collection import Collection

            if self.collection.hash_mode == Collection.HASH_RAW:
                pass
            elif self.collection.hash_mode == Collection.HASH_NO_NUMBERS:
                try:
                    content = re.sub("[0-9]+", "0", content)
                except UnicodeDecodeError:
                    pass
            else:
                raise Exception("HASH_MODE not supported")
            content = content.encode("utf-8")
        else:
            if not isinstance(content, bytes):
                raise ValueError("content must be a string")

        return settings.HASHING_ALGO(content).hexdigest()

    def _index_log(self, s, stats, verbose):
        if not verbose:
            return
        n = now()
        crawl_logger.debug(f"{n - stats['prev']} {s}")
        stats["prev"] = n

    def _clear_base_content(self):
        self.redirect_url = None
        self.too_many_redirects = False
        self.content = ""
        self.content_hash = ""
        self.normalized_content = ""
        self.title = ""
        self.normalized_title = ""
        self.mimetype = ""
        self.manual_crawl = False
        self.mime_plugins_result = ""

    def _clear_dump_content(self):
        from .models import Link

        Link.objects.filter(doc_from=self).delete()
        self.delete_html()
        self.delete_screenshot()
        self.delete_thumbnail()

    def _parse_xml(self, page, stats, verbose):
        parsed = feedparser.parse(page.content)
        if len(getattr(parsed, "entries", [])) == 0:
            return

        for entry in parsed["entries"]:
            if entry.get("updated_parsed"):
                entry["updated_datetime"] = datetime.fromtimestamp(mktime(entry["updated_parsed"]))

        if getattr(parsed.feed, "title", None):
            page.title = parsed.feed.title
            self.title = parsed.feed.title

        template = get_template("se/feed.html")
        context = {"feed": parsed}
        page.content = template.render(context).encode("utf-8")
        page.soup = None

        crawl_logger.debug(f"{self.url} is a rss/atom feed with {len(parsed['entries'])} items")

    @staticmethod
    def _normalized_title(title):
        return remove_accent(title)

    @staticmethod
    def _normalized_content(content):
        return remove_accent(content)

    @staticmethod
    def _url_matches_regex(url, regex_pg):
        """Check if URL matches PostgreSQL regex pattern."""
        if not regex_pg:
            return False

        from django.db import connection

        cursor = connection.cursor()
        cursor.execute("SELECT 1 WHERE %s ~ %s", [url, regex_pg])
        return bool(cursor.fetchone())

    def _parse_text(self, page, stats, verbose):
        crawl_logger.debug(f"parsing {self.url}")
        links = page.dom_walk(self.collection, True, self)
        text = links["text"]

        self._index_log(f"text / {len(links['links'])} links extraction", stats, verbose)

        self.content = text
        self.normalized_content = self._normalized_content(self.content)
        self.lang_iso_639_1, self.vector_lang = self._get_lang((page.title or "") + "\n" + text)
        self._index_log("remove accent", stats, verbose)

        # The bulk request triggers a deadlock: Link.objects.bulk_create(links['links'])
        for link in links["links"]:
            link.save()
        if len(links["links"]) > 0:
            from .models import WorkerStats

            WorkerStats.wake_up()
        self._index_log("bulk", stats, verbose)
        return links

    def index(self, page, verbose=False):
        crawl_logger.debug(f"indexing {self.url}")
        from .collection import Collection

        n = now()
        stats = {"prev": n}
        self._index_log("start", stats, verbose)

        current_hash = self.content_hash
        manual_crawl = self.manual_crawl
        first_crawl = self.crawl_first is None

        self._clear_base_content()
        self._index_log("queuing links", stats, verbose)

        beautified_url = url_beautify(page.url)
        normalized_url = beautified_url.split("://", 1)[1].replace("/", " ").strip()
        self.normalized_url = remove_accent(normalized_url)
        if page.title:
            self.title = page.title
        else:
            self.title = beautified_url

        self.normalized_title = self._normalized_title(self.title)
        self.mimetype = page.mimetype
        self.hidden = self.collection.hide_documents

        self.crawl_last = n
        if not self.crawl_first:
            self.crawl_first = n

        if not re.match(self.collection.mimetype_regex, self.mimetype):
            self._schedule_next(False, self.collection)

            crawl_logger.debug(f"skipping {self.url} due to mimetype {self.mimetype}")
            return

        links = page.dom_walk(self.collection, False, None)
        self.content = links["text"]
        crawl_logger.debug(f"queued links {len(links['links'])}")

        # self.content may be empty if the page is not text-based, in this case we use the page content
        _hash_content = self.content if self.mimetype.startswith("text/") else page.content
        self.content_hash = self._hash_content(_hash_content)

        self._schedule_next(current_hash != self.content_hash)

        webhook_trigger_cond = {Webhook.TRIGGER_COND_ALWAYS}

        if first_crawl:
            webhook_trigger_cond |= {
                Webhook.TRIGGER_COND_DISCOVERY,
                Webhook.TRIGGER_COND_ON_CHANGE,
                Webhook.TRIGGER_COND_MANUAL,
            }
        if current_hash != self.content_hash:
            webhook_trigger_cond |= {Webhook.TRIGGER_COND_ON_CHANGE, Webhook.TRIGGER_COND_MANUAL}
        if manual_crawl:
            webhook_trigger_cond |= {Webhook.TRIGGER_COND_MANUAL}

        if current_hash == self.content_hash:
            if self.collection.recrawl_condition == Collection.RECRAWL_COND_ON_CHANGE or (
                self.collection.recrawl_condition == Collection.RECRAWL_COND_MANUAL and not manual_crawl
            ):
                Webhook.trigger(self.collection.webhooks.filter(trigger_condition__in=webhook_trigger_cond), self)
                crawl_logger.debug(f"{self.url} has not changed, skipping indexing (content hash {self.content_hash})")
                return
        if current_hash != self.content_hash:
            self.modified_date = n

        self._clear_dump_content()
        self.tags.add(*self.collection.tags.values_list("pk", flat=True))

        if self.mimetype.startswith("text/"):
            self._parse_xml(page, stats, verbose)
            links = self._parse_text(page, stats, verbose)

        if self.mimetype.startswith("text/"):
            if self.collection.thumbnail_mode in (
                Collection.THUMBNAIL_MODE_PREVIEW,
                Collection.THUMBNAIL_MODE_PREV_OR_SCREEN,
            ):
                if DocumentMeta.create_preview(page, self.image_name()):
                    self.has_thumbnail = True

            if not self.has_thumbnail and self.collection.thumbnail_mode in (
                Collection.THUMBNAIL_MODE_PREV_OR_SCREEN,
                Collection.THUMBNAIL_MODE_SCREENSHOT,
            ):
                self.collection.get_browser(url=self.url).create_thumbnail(self.url, self.image_name())
                self.has_thumbnail = True
        elif self.mimetype.startswith("image/"):
            if self.collection.thumbnail_mode in (
                Collection.THUMBNAIL_MODE_PREVIEW,
                Collection.THUMBNAIL_MODE_PREV_OR_SCREEN,
                Collection.THUMBNAIL_MODE_SCREENSHOT,
            ):
                if DocumentMeta.preview_file_from_url(self.url, self.image_name()):
                    self.has_thumbnail = True

        if self.mimetype.startswith("text/"):
            from .models import FavIcon

            FavIcon.extract(self, page)
            self._index_log("favicon", stats, verbose)

            if self.collection.snapshot_html:
                if self.collection.remove_nav_elements == Collection.REMOVE_NAV_FROM_ALL:
                    page.remove_nav_elements()
                snapshot = HTMLSnapshot(page, self.collection)
                snapshot.snapshot()
                self.has_html_snapshot = True
        else:
            if self.collection.snapshot_html:
                HTMLCache.write_asset(self.url, page.content, page, mimetype=self.mimetype)
                self.has_html_snapshot = True

        if self.mimetype.startswith("text/"):
            if self.collection.take_screenshots:
                self.screenshot_index(links["links"])

        self._index_log("done", stats, verbose)

        if page.script_result:
            from .rest_api import DocumentSerializer

            serializer = DocumentSerializer(self, data=page.script_result, partial=True)
            serializer.user_doc_update("Javascript")

        MimePlugin.run_for_document(self, page)
        Webhook.trigger(self.collection.webhooks.filter(trigger_condition__in=webhook_trigger_cond), self)

        if not self.title:
            self.title = self.url

        self.retries = 0

    def convert_to_jpg(self):
        d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, self.image_name())

        for i in range(self.screenshot_count):
            src = f"{d}_{i}.png"
            dst = f"{d}_{i}.jpg"
            crawl_logger.debug(f"Converting {src} to {dst}")

            img = Image.open(src)
            img = img.convert("RGB")  # Remove alpha channel from the png
            img.save(dst, "jpeg")
            os.unlink(src)

    def screenshot_index(self, links):
        from .collection import Collection

        if self.collection.remove_nav_elements in (
            Collection.REMOVE_NAV_FROM_ALL,
            Collection.REMOVE_NAV_FROM_SCREENSHOT,
        ):
            browser = self.collection.get_browser(url=self.url)
            browser.remove_nav_elements()

        browser = self.collection.get_browser(url=self.url)
        img_count = browser.take_screenshots(self.collection, self.image_name())
        crawl_logger.debug(f"took {img_count} screenshots for {self.url} with {browser}")
        self.screenshot_count = img_count
        self.screenshot_format = self.collection.screenshot_format
        w, h = browser.screen_size()
        self.screenshot_size = f"{w}x{h}"

        if self.collection.screenshot_format == Document.SCREENSHOT_JPG:
            self.convert_to_jpg()

        browser.scroll_to_page(0)
        for i, link in enumerate(links):
            loc = browser.get_link_pos_abs(link.css_selector)
            if loc == {}:
                continue
            for attr in ("elemLeft", "elemTop", "elemRight", "elemBottom"):
                if not isinstance(loc[attr], (int, float)):
                    break
            else:
                link.screen_pos = ",".join(
                    [
                        str(int(loc["elemLeft"])),
                        str(int(loc["elemTop"])),
                        str(int(loc["elemRight"] - loc["elemLeft"])),
                        str(int(loc["elemBottom"] - loc["elemTop"])),
                    ]
                )
                link.save()

    def set_error(self, err):
        self.error = err
        if err == "":
            self.error_hash = ""
        else:
            self.error_hash = md5(err.encode("utf-8"), usedforsecurity=False).hexdigest()

    @staticmethod
    def manual_queue(url, collection, show_on_homepage):
        crawl_depth = collection.recursion_depth

        doc, created = Document.objects.wo_content().get_or_create(
            url=url, collection=collection, defaults={"crawl_recurse": crawl_depth}
        )
        if not created:
            doc.crawl_next = now()
            if crawl_depth is not None:
                doc.crawl_recurse = crawl_depth

        doc.manual_crawl = True
        doc.show_on_homepage = show_on_homepage
        doc.save()
        return doc

    @staticmethod
    def queue(url, collection, parent):
        from .models import ExcludedUrl

        if ExcludedUrl.objects.filter(url=url, starting_with=False).first():
            crawl_logger.debug(f"skipping ExcludedUrl {url}")
            return None

        if ExcludedUrl.objects.filter(starting_with=True).extra(where=["starts_with(%s, url)"], params=[url]).first():
            crawl_logger.debug(f"skipping ExcludedUrl {url}")
            return None

        crawl_logger.debug(f"Queueing {url} collection {collection} (parent: {parent})")

        # Check collection-specific exclusions
        if Document._url_matches_regex(url, collection.excluded_regex_pg):
            crawl_logger.debug(f"skipping {url} - excluded by excluded_regex")
            return None

        # Check if URL should be crawled (unlimited_regex for unlimited recursion, limited_regex for depth-based)
        should_crawl = False

        crawl_recurse = collection.recursion_depth
        should_crawl = Document._url_matches_regex(url, collection.unlimited_regex_pg)
        if should_crawl:
            crawl_logger.debug(f"queueing {url} - matches unlimited_regex")
        else:
            crawl_logger.debug(f"queueing {url} - did not match unlimited_regex")

        if not should_crawl and collection.limited_regex_pg and parent:
            crawl_logger.debug(f"queueing {url} - attempting limited_regex")

            if Document._url_matches_regex(url, collection.limited_regex_pg) and parent.crawl_recurse > 0:
                # The url matches limited_regex, so we check if there is still depth to crawl
                crawl_recurse = parent.crawl_recurse - 1
                should_crawl = True
                crawl_logger.debug(f"queueing {url} - matches limited_regex with full depth")

        if not should_crawl:
            # Check cross-collection queueing only if the parent document is in the same collection (otherwise we already did it)
            if parent and parent.collection == collection:
                crawl_logger.debug(
                    f"URL {url} doesn't match collection {collection.name} patterns - checking cross-collection crawl"
                )
                # Check cross-collection queueing if enabled
                matching_collection = None

                crawl_logger.debug(
                    f"Collection {collection.name} queue_to_any_collection: {collection.queue_to_any_collection}"
                )
                crawl_logger.debug(
                    f"Collection {collection.name} queue_to_collections exists: {collection.queue_to_collections.exists()}"
                )

                if collection.queue_to_any_collection:
                    # Check all collections
                    crawl_logger.debug(f"Checking all collections for URL {url}")
                    from .collection import Collection

                    matching_collection = Collection.get_from_url(url)
                    crawl_logger.debug(f"get_from_url returned: {matching_collection}")
                elif collection.queue_to_collections.exists():
                    # Check only selected collections
                    crawl_logger.debug(f"Checking selected collections for URL {url}")
                    from .collection import Collection

                    target_collections = list(collection.queue_to_collections.all())
                    crawl_logger.debug(f"Target collections: {[c.name for c in target_collections]}")
                    matching_collection = Collection.get_from_url(url, target_collections)
                    crawl_logger.debug(f"get_from_url with filter returned: {matching_collection}")

                if matching_collection and matching_collection != collection:
                    mode = "any" if collection.queue_to_any_collection else "specific"
                    crawl_logger.debug(
                        f"cross-collection queueing {url} - found matching collection {matching_collection} ({mode} mode)"
                    )
                    return Document.queue(url, matching_collection, parent)

                crawl_logger.debug(f"skipping {url} - does not match unlimited_regex or limited_regex")
                return

            # No parent means this is the seed URL, we always queue it
            crawl_recurse = collection.recursion_depth

        doc, created = Document.objects.wo_content().get_or_create(
            url=url,
            collection=collection,
            defaults={"hidden": collection.hide_documents, "crawl_recurse": crawl_recurse},
        )
        if not created:
            doc.crawl_recurse = max(doc.crawl_recurse, crawl_recurse)
        return doc

    def _schedule_next(self, changed):
        from .collection import Collection

        stop = False
        # In new model, stop crawling if no more depth remaining for recursive documents
        if self.crawl_recurse == 0:
            # Check if this URL matches unlimited_regex (should always recrawl) or only limited_regex

            if not Document._url_matches_regex(self.url, self.collection.unlimited_regex_pg):
                stop = True

        if self.collection.recrawl_freq == Collection.RECRAWL_FREQ_NONE or stop:
            self.crawl_next = None
            self.crawl_dt = None
        elif self.collection.recrawl_freq == Collection.RECRAWL_FREQ_CONSTANT:
            self.crawl_next = self.crawl_last + self.collection.recrawl_dt_min
            self.crawl_dt = None
        elif self.collection.recrawl_freq == Collection.RECRAWL_FREQ_ADAPTIVE:
            if self.crawl_dt is None:
                self.crawl_dt = self.collection.recrawl_dt_min
            elif not changed:
                self.crawl_dt = min(self.collection.recrawl_dt_max, self.crawl_dt * 2)
            else:
                self.crawl_dt = max(self.collection.recrawl_dt_min, self.crawl_dt / 2)
            self.crawl_next = self.crawl_last + self.crawl_dt

    @staticmethod
    def crawl(worker_no):
        from .models import Link, WorkerStats

        doc = Document.pick_queued(worker_no)
        if doc is None:
            return False

        if getattr(settings, "TEST_MODE", False):
            worker_stats = WorkerStats.get_worker(worker_no)
        else:
            worker_stats = WorkerStats.objects.get(worker_no=worker_no)
        if worker_stats.state != "running":
            worker_stats.update_state("running")

        if settings.DEBUG:
            queued_count = Document.objects.wo_content().filter(crawl_last__isnull=True).count()
            indexed_count = Document.objects.wo_content().filter(crawl_last__isnull=False).count()

            crawl_logger.debug(
                f"Worker:{worker_no} Queued:{queued_count} Indexed:{indexed_count} Id:{doc.id} {doc.url} ..."
            )

        while True:
            # Loop until we stop redirecting
            crawl_logger.debug(f"Crawling {doc.url} (collection: {doc.collection})")
            try:
                WorkerStats.objects.filter(id=worker_stats.id).update(doc_processed=models.F("doc_processed") + 1)
                Document.objects.wo_content().filter(id=doc.id).update(retries=models.F("retries") + 1)
                doc.worker_no = None
                doc.crawl_last = now()

                if doc.url.startswith("http://") or doc.url.startswith("https://"):
                    domain = Domain.get_from_url(doc.url)

                    if not domain.robots_authorized(doc.url, doc.collection):
                        crawl_logger.debug(f"{doc.url} rejected by robots.txt")
                        doc.robotstxt_rejected = True
                        n = now()
                        doc.crawl_last = n
                        if not doc.crawl_first:
                            doc.crawl_first = n
                        doc.crawl_next = None
                        doc.crawl_dt = None
                        doc._clear_base_content()
                        doc._clear_dump_content()
                        doc.save()
                        break
                    else:
                        doc.robotstxt_rejected = False

                    try:
                        page = doc.collection.url_get(doc.url, domain)
                    except AuthElemFailed as e:
                        doc.content = e.page.content.decode("utf-8")
                        doc._schedule_next(True)
                        doc.set_error(f"Locating authentication element failed at {e.page.url}:\n{e.args[0]}")
                        doc._clear_base_content()
                        doc._clear_dump_content()
                        doc.save()
                        crawl_logger.error(f"Locating authentication element failed at {e.page.url}:\n{e.args[0]}")
                        break
                    except SkipIndexing as e:
                        doc._schedule_next(False)
                        doc.set_error(e.args[0])
                        doc._clear_base_content()
                        doc._clear_dump_content()
                        doc.save()
                        crawl_logger.debug(f"{doc.url}: {e.args[0]}")
                        break

                    if page.url == doc.url:
                        doc.set_error("")
                        doc.index(page)
                        doc.save()
                        Link.objects.filter(extern_url=doc.url).update(extern_url=None, doc_to=doc)
                        break
                    else:
                        if not page.redirect_count:
                            raise Exception(f"redirect not set {doc.url} -> {page.url}")
                        crawl_logger.debug(
                            f"{worker_no} redirect {doc.url} -> {page.url} (redirect no {page.redirect_count})"
                        )
                        doc._schedule_next(doc.redirect_url != page.url)
                        doc._clear_base_content()
                        doc._clear_dump_content()
                        doc.set_error("")
                        doc.redirect_url = page.url
                        doc.save()

                        # Process the page if it's new, otherwise skip it since it'll be processed depending on `crawl_next`
                        if Document.objects.wo_content().filter(url=page.url, collection=doc.collection).count():
                            break

                        doc = Document.pick_or_create(page.url, doc.collection, worker_no)
                        if doc is None:
                            break
                else:
                    break
            except Exception as e:  # noqa
                doc.set_error(format_exc())
                doc._schedule_next(True)
                doc.retries = 0
                doc.save()
                crawl_logger.error(format_exc())
                if getattr(settings, "TEST_MODE", False):
                    raise
                break

            worker_stats.refresh_from_db()
            if worker_stats.state == "paused":
                doc.worker_no = None
                doc.save()
                break

        return True

    @staticmethod
    def crawl_queue(full_queue):
        current_now = now()

        # Returns only pending, ready to be processed documents if with_pending is False
        queue = (
            Document.objects.wo_content()
            .filter(
                models.Q(crawl_last__isnull=True) | models.Q(crawl_last__isnull=False, crawl_next__lte=current_now),
                retries__lte=settings.SOSSE_WORKER_CRASH_RETRY,
                worker_no__isnull=True,
            )
            .order_by(
                "-manual_crawl",  # to prioritize manual crawls
                "-crawl_last",  # to prioritize documents with no crawl_last
                "crawl_next",
                "id",
            )
        )

        if not full_queue:
            return queue

        queue = list(queue[: Document.DISPLAY_QUEUE_SIZE])

        # Pending not ready
        if len(queue) < Document.DISPLAY_QUEUE_SIZE:
            queue = queue + list(
                Document.objects.wo_content()
                .filter(
                    models.Q(crawl_last__isnull=False, crawl_next__gt=current_now),
                    retries__lte=settings.SOSSE_WORKER_CRASH_RETRY,
                    worker_no__isnull=True,
                )
                .exclude(
                    id__in=[d.id for d in queue],
                )
                .order_by(
                    "-crawl_next",
                    "-id",
                )[: Document.DISPLAY_QUEUE_SIZE - len(queue)]
            )

        queue.reverse()

        # In progress
        queue += list(
            Document.objects.wo_content()
            .filter(worker_no__isnull=False)
            .exclude(id__in=[d.id for d in queue])
            .order_by("id")
        )
        for doc in queue:
            doc.pending = True

        # Last crawled
        history = list(
            Document.objects.wo_content()
            .filter(
                models.Q(crawl_next__isnull=True) | models.Q(crawl_next__gt=now()),
                crawl_last__isnull=False,
            )
            .exclude(id__in=[d.id for d in queue])
            .order_by("-crawl_last")[: Document.DISPLAY_QUEUE_SIZE]
        )

        for doc in history:
            doc.in_history = True
        return queue + history

    @staticmethod
    def pick_queued(worker_no):
        while True:
            doc = Document.crawl_queue(False).first()
            if doc is None:
                return None

            updated = (
                Document.objects.wo_content().filter(id=doc.id, worker_no__isnull=True).update(worker_no=worker_no)
            )

            if updated == 0:
                sleep(0.1)
                continue

            try:
                doc.refresh_from_db()
            except Document.DoesNotExist:
                sleep(0.1)
                continue

            return doc

    @staticmethod
    def pick_or_create(url, collection, worker_no):
        doc, created = Document.objects.wo_content().get_or_create(
            url=url, collection=collection, defaults={"worker_no": worker_no}
        )
        if created:
            return doc

        updated = (
            Document.objects.wo_content()
            .filter(id=doc.id, collection=collection, worker_no__isnull=True)
            .update(worker_no=worker_no)
        )

        if updated == 0:
            return None

        try:
            doc.refresh_from_db()
        except Document.DoesNotExist:
            pass

        return doc

    def delete_html(self):
        if self.has_html_snapshot:
            if self.mimetype and self.mimetype.startswith("text/"):
                HTMLAsset.html_delete_url(self.url)
            else:
                for asset in HTMLAsset.objects.filter(url=self.url):
                    asset.remove_ref()
            self.has_html_snapshot = False

    def delete_screenshot(self):
        if self.screenshot_count:
            d = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, self.image_name())

            for i in range(self.screenshot_count):
                filename = f"{d}_{i}.{self.screenshot_format}"
                if os.path.exists(filename):
                    os.unlink(filename)
            self.screenshot_count = 0

    def delete_thumbnail(self):
        if self.has_thumbnail:
            f = os.path.join(settings.SOSSE_THUMBNAILS_DIR, self.image_name()) + ".jpg"
            if os.path.exists(f):
                os.unlink(f)
            self.has_thumbnail = False

    def delete_all(self):
        self.delete_html()
        self.delete_screenshot()
        self.delete_thumbnail()

    def default_domain(self):
        return Domain.get_from_url(self.url)

    def webhook_in_error(self):
        for webhook_id, webhook in self.webhooks_result.items():
            if (
                webhook.get("status_code") and (webhook.get("status_code") < 200 or webhook.get("status_code") >= 300)
            ) or webhook.get("error"):
                webhook = Webhook.objects.filter(pk=webhook_id).first()
                name = webhook.name if webhook else f"Deleted Webhook {webhook_id}"
                return name
        return None

    def get_content_file(self):
        if self.has_html_snapshot:
            asset = HTMLAsset.objects.filter(url=self.url).first()
            if asset:
                asset_path = settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename
                if os.path.exists(asset_path):
                    return asset_path

        return None
