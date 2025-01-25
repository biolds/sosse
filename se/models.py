# Copyright 2022-2025 Laurent Defert
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
import os
import re
import urllib.parse
from base64 import b64decode, b64encode
from datetime import timedelta

from defusedxml import ElementTree
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.http import QueryDict
from django.utils.timezone import now

from .browser_request import BrowserRequest
from .document import Document
from .online import online_status
from .url import absolutize_url, url_remove_fragment, url_remove_query_string

crawl_logger = logging.getLogger("crawler")


class Link(models.Model):
    # doc_from can be null when a document is deleted,
    # in this case the link is not deleted to keep its `text` to weight
    # in the ranking
    doc_from = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="links_to",
    )
    # doc_to can be null when storing extern_url
    doc_to = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="linked_from",
    )
    text = models.TextField(null=True, blank=True)
    pos = models.PositiveIntegerField()
    link_no = models.PositiveIntegerField()
    extern_url = models.TextField(null=True, blank=True)
    screen_pos = models.CharField(max_length=64, null=True, blank=True)
    in_nav = models.BooleanField(default=False)

    class Meta:
        unique_together = ("doc_from", "link_no")

    def pos_left(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(",")[0]

    def pos_top(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(",")[1]

    def pos_bottom(self):
        if not self.screen_pos:
            return 0
        return str(100 - int(self.screen_pos.split(",")[1]))

    def pos_width(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(",")[2]

    def pos_height(self):
        if not self.screen_pos:
            return 0
        return self.screen_pos.split(",")[3]


class AuthField(models.Model):
    key = models.CharField(max_length=256, verbose_name="<input> name attribute")
    value = models.CharField(max_length=256)
    crawl_policy = models.ForeignKey("CrawlPolicy", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "authentication field"


MINUTELY = "M"
DAILY = "D"
FREQUENCY = (
    (MINUTELY, MINUTELY),
    (DAILY, DAILY),
)


class WorkerStats(models.Model):
    STATE = (
        ("idle", "Idle"),
        ("running", "Running"),
        ("paused", "Paused"),
    )

    doc_processed = models.PositiveIntegerField(default=0)
    worker_no = models.IntegerField()
    pid = models.PositiveIntegerField()
    state = models.CharField(max_length=8, choices=STATE, default="idle")

    @classmethod
    def get_worker(cls, worker_no):
        return cls.objects.update_or_create(worker_no=worker_no, defaults={"pid": os.getpid()})[0]

    def update_state(self, state):
        WorkerStats.objects.filter(worker_no=self.worker_no).exclude(state="paused").update(state=state)

    @classmethod
    def live_state(cls):
        workers = cls.objects.order_by("worker_no")
        for w in workers:
            args = []
            if os.path.exists(f"/proc/{w.pid}/cmdline"):
                with open(f"/proc/{w.pid}/cmdline", "br") as fd:
                    args = fd.read().split(b"\0")

            for i, arg in enumerate(args):
                if i == len(args) - 1:
                    continue
                # Debian install
                if arg == b"sosse.sosse_admin" and args[i + 1] == b"crawl":
                    break
                # Pip install
                if arg.endswith(b"sosse-admin") and args[i + 1] == b"crawl":
                    break
            else:
                w.pid = "-"
                w.state = "exited"

            if w.state != "exited":
                w.doc = Document.objects.filter(worker_no=w.worker_no).first()
        return workers


class CrawlerStats(models.Model):
    t = models.DateTimeField()
    doc_count = models.PositiveIntegerField()
    queued_url = models.PositiveIntegerField()
    indexing_speed = models.PositiveIntegerField(blank=True, null=True)
    freq = models.CharField(max_length=1, choices=FREQUENCY)

    @staticmethod
    def create(t):
        CrawlerStats.objects.filter(t__lt=t - timedelta(hours=24), freq=MINUTELY).delete()
        CrawlerStats.objects.filter(t__lt=t - timedelta(days=365), freq=DAILY).delete()

        doc_processed = WorkerStats.objects.filter().aggregate(s=models.Sum("doc_processed")).get("s", 0) or 0
        WorkerStats.objects.update(doc_processed=0)

        doc_count = Document.objects.count()
        queued_url = (
            Document.objects.filter(crawl_last__isnull=True).count()
            + Document.objects.filter(crawl_next__lte=now()).count()
        )

        today = now().replace(hour=0, minute=0, second=0, microsecond=0)
        entry, _ = CrawlerStats.objects.get_or_create(
            t=today,
            freq=DAILY,
            defaults={"doc_count": 0, "queued_url": 0, "indexing_speed": 0},
        )
        entry.indexing_speed += doc_processed
        entry.doc_count = doc_count
        entry.queued_url = max(queued_url, entry.queued_url)
        entry.save()

        CrawlerStats.objects.create(
            t=t,
            doc_count=doc_count,
            queued_url=queued_url,
            indexing_speed=doc_processed,
            freq=MINUTELY,
        )


def validate_search_url(value):
    if "{searchTerms}" not in value and "{searchTermsBase64}" not in value:
        raise ValidationError(
            "This field must contain the search url with a {searchTerms} or a {searchTermsBase64} string parameter"
        )


class SearchEngine(models.Model):
    short_name = models.CharField(unique=True, max_length=32, blank=True, default="")
    long_name = models.CharField(max_length=48, blank=True, default="")
    description = models.CharField(max_length=1024, blank=True, default="")
    html_template = models.CharField(max_length=2048, validators=[validate_search_url])
    shortcut = models.CharField(max_length=16, blank=True)

    def __str__(self):
        return self.short_name

    @classmethod
    def parse_odf(cls, content):
        root = ElementTree.fromstring(content)
        ns = root.tag[: -len("OpenSearchDescription")]

        short_name_elem = root.find(ns + "ShortName")
        if short_name_elem is None:
            return

        short_name = short_name_elem.text
        se = None
        try:
            se = cls.objects.get(short_name=short_name)
        except SearchEngine.DoesNotExist:
            se = SearchEngine(short_name=short_name)

        long_name = root.find(ns + "LongName")
        if long_name is None:
            long_name = short_name
        else:
            long_name = long_name.text
        se.long_name = long_name
        se.description = root.find(ns + "Description").text

        for elem in root.findall(ns + "Url"):
            if elem.get("type") == "text/html":
                se.html_template = elem.get("template")
            elif elem.get("type") == "application/x-suggestions+json":
                se.suggestion_template = elem.get("template")

        se.shortcut = short_name.lower().split(" ")[0]
        se.save()

    @classmethod
    def parse_xml_file(cls, f):
        with open(f) as fd:
            buf = fd.read()

        cls.parse_odf(buf)

    def get_search_url(self, query):
        se_url = urllib.parse.urlsplit(self.html_template)

        # In url path
        if "{searchTerms}" in se_url.path:
            query = urllib.parse.quote_plus(query)
            se_url_path = se_url.path.replace("{searchTerms}", query)
            se_url = se_url._replace(path=se_url_path)
            return urllib.parse.urlunsplit(se_url)

        if "{searchTermsBase64}" in se_url.path:
            query = urllib.parse.quote_plus(b64encode(query.encode("utf-8")).decode("utf-8"))
            se_url_path = se_url.path.replace("{searchTermsBase64}", query)
            se_url = se_url._replace(path=se_url_path)
            return urllib.parse.urlunsplit(se_url)

        # In url fragment (the part after #)
        if "{searchTerms}" in se_url.fragment:
            query = urllib.parse.quote_plus(query)
            se_url_frag = se_url.fragment.replace("{searchTerms}", query)
            se_url = se_url._replace(fragment=se_url_frag)
            return urllib.parse.urlunsplit(se_url)

        if "{searchTermsBase64}" in se_url.fragment:
            se_url_frag = se_url.fragment.replace(
                "{searchTermsBase64}", b64encode(query.encode("utf-8")).decode("utf-8")
            )
            se_url = se_url._replace(fragment=se_url_frag)
            return urllib.parse.urlunsplit(se_url)

        # In url parameters
        se_params = urllib.parse.parse_qs(se_url.query)
        for key, val in se_params.items():
            val = val[0]
            if "{searchTerms}" in val:
                se_params[key] = [val.replace("{searchTerms}", query)]
                break
            if "{searchTermsBase64}" in val:
                se_params[key] = [
                    val.replace(
                        "{searchTermsBase64}",
                        b64encode(query.encode("utf-8")).decode("utf-8"),
                    )
                ]
                break
        else:
            raise Exception("could not find {searchTerms} or {searchTermsBase64} parameter")

        se_url_query = urllib.parse.urlencode(se_params, doseq=True)
        se_url = se_url._replace(query=se_url_query)
        return urllib.parse.urlunsplit(se_url)

    @classmethod
    def should_redirect(cls, query, request=None):
        se = None
        for i, w in enumerate(query.split()):
            if not w.startswith(settings.SOSSE_SEARCH_SHORTCUT_CHAR):
                continue

            se_str = w[len(settings.SOSSE_SEARCH_SHORTCUT_CHAR) :]
            if settings.SOSSE_DEFAULT_SEARCH_REDIRECT and se_str == settings.SOSSE_SOSSE_SHORTCUT:
                return

            se = SearchEngine.objects.filter(shortcut=se_str).first()
            if se is None:
                continue

            q = query.split()
            del q[i]
            query = " ".join(q)
            break
        else:
            if settings.SOSSE_ONLINE_SEARCH_REDIRECT and request and online_status(request) == "online":
                se = SearchEngine.objects.filter(short_name=settings.SOSSE_ONLINE_SEARCH_REDIRECT).first()

            # Follow the default redirect if a query was provided
            if settings.SOSSE_DEFAULT_SEARCH_REDIRECT and query.strip():
                se = SearchEngine.objects.filter(short_name=settings.SOSSE_DEFAULT_SEARCH_REDIRECT).first()

        if se:
            return se.get_search_url(query)


class FavIcon(models.Model):
    url = models.TextField(unique=True)
    content = models.BinaryField(null=True, blank=True)
    mimetype = models.CharField(max_length=64, null=True, blank=True)
    missing = models.BooleanField(default=True)

    @classmethod
    def extract(cls, doc, page):
        url = cls._get_url(page)

        if url is None:
            url = "/favicon.ico"

        url = absolutize_url(doc.url, url)
        url = url_remove_query_string(url_remove_fragment(url))

        favicon, created = FavIcon.objects.get_or_create(url=url)
        doc.favicon = favicon

        if not created:
            return

        try:
            if url.startswith("data:"):
                data = url.split(":", 1)[1]
                mimetype, data = data.split(";", 1)
                encoding, data = data.split(",", 1)
                if encoding != "base64":
                    raise Exception(f"encoding {encoding} not supported")
                data = b64decode(data)
                favicon.mimetype = mimetype
                favicon.content = data
                favicon.missing = False
            else:
                page = BrowserRequest.get(url, check_status=True)
                from magic import from_buffer as magic_from_buffer

                favicon.mimetype = magic_from_buffer(page.content, mime=True)
                if favicon.mimetype.startswith("image/"):
                    favicon.content = page.content
                    favicon.missing = False
        except Exception:  # nosec B110
            pass

        favicon.save()

    @classmethod
    def _get_url(cls, page):
        parsed = page.get_soup()
        links = parsed.find_all("link", rel=re.compile("shortcut icon", re.IGNORECASE))
        if links == []:
            links = parsed.find_all("link", rel=re.compile("icon", re.IGNORECASE))

        if len(links) == 0:
            return None
        if len(links) == 1:
            return links[0].get("href")

        for prefered_size in ("32x32", "16x16"):
            for link in links:
                if link.get("sizes") == prefered_size:
                    return link.get("href")

        return links[0].get("href")


class SearchHistory(models.Model):
    query = models.TextField()
    querystring = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @classmethod
    def save_history(cls, request, q):
        from .search import FILTER_RE

        params = {}

        queryparams = ""
        for key, val in request.GET.items():
            if not re.match(FILTER_RE, key) and key not in ("l", "doc_lang", "s", "q"):
                continue
            params[key] = val

            if not key.startswith("fv"):
                continue

            if queryparams:
                queryparams += " "
            queryparams += val

        if q:
            if queryparams:
                q = f"{q} ({queryparams})"
        else:
            q = queryparams

        qd = QueryDict(mutable=True)
        qd.update(params)
        qs = qd.urlencode()

        if not request.user.is_anonymous:
            last = SearchHistory.objects.filter(user=request.user).order_by("date").last()
            if last and last.querystring == qs:
                return

            if not q and not qs:
                return

            SearchHistory.objects.create(querystring=qs, query=q, user=request.user)


class ExcludedUrl(models.Model):
    url = models.TextField(unique=True)
    starting_with = models.BooleanField(default=False, help_text="Exclude all urls starting with the url pattern")
    comment = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Excluded URL"
