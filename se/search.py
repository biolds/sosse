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
import re
import uuid
from collections import OrderedDict
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank
from django.core.paginator import Paginator
from django.db import models
from django.http import QueryDict
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .collection import Collection
from .document import Document, extern_link_flags, remove_accent
from .html_asset import HTMLAsset
from .models import SearchEngine, SearchHistory
from .search_form import FILTER_FIELDS, SearchForm
from .tag import Tag
from .utils import human_nb
from .views import RedirectException, UserView

logger = logging.getLogger("web")

FILTER_RE = "(ft|ff|fo|fv|fc)[0-9]+$"


def remove_query_param(request, key, value=None):
    url_parts = list(urlparse(request.get_full_path()))
    query = QueryDict(url_parts[4], mutable=True)

    if key in query:
        if value is None:
            query.pop(key)
        else:
            values = query.getlist(key)
            if value in values:
                values.remove(value)
                if values:
                    query.setlist(key, values)
                else:
                    query.pop(key)

    url_parts[4] = query.urlencode()
    return urlunparse(url_parts)


def add_query_param(request, key, value):
    url_parts = list(urlparse(request.get_full_path()))
    query = QueryDict(url_parts[4], mutable=True)

    if key in query:
        values = query.getlist(key)
        if value not in values:
            values.append(value)
            query.setlist(key, values)
    else:
        query[key] = value

    url_parts[4] = query.urlencode()
    return urlunparse(url_parts)


def get_documents_from_request(request, form, stats_call=False):
    filters = {}
    for key, val in request.GET.items():
        if not re.match(FILTER_RE, key):
            continue

        filter_no = key[2:]
        f = filters.get(filter_no, {})
        f[key[:2]] = val
        filters[filter_no] = f
    keys = sorted(filters.keys())
    params = [filters[k] for k in keys]
    return get_documents(request, params, form, stats_call)


def get_documents(request, params, form, stats_call):
    REQUIRED_KEYS = ("ft", "ff", "fo", "fv")

    results = Document.objects.w_content().annotate(rank=models.Value(1.0))
    has_query = False

    q = form.cleaned_data.get("q", "")
    q = remove_accent(q)
    query = None
    if q:
        has_query = True
        lang = form.cleaned_data["l"]

        query = SearchQuery(q, config=lang, search_type="websearch")
        all_results = (
            Document.objects.w_content()
            .filter(vector=query)
            .annotate(
                rank=SearchRank(models.F("vector"), query),
            )
        )
        results = all_results.exclude(rank__lte=0.01)

        if results.count() == 0:
            results = all_results

    include_hidden = form.cleaned_data.get("i", False) and True

    if not request.user.has_perm("se.document_change") or not include_hidden:
        results = results.exclude(hidden=True)

    if settings.SOSSE_EXCLUDE_NOT_INDEXED:
        results = results.exclude(crawl_last__isnull=True)
    if settings.SOSSE_EXCLUDE_REDIRECT:
        results = results.filter(redirect_url__isnull=True)

    for f in params:
        cont = True
        for k in REQUIRED_KEYS:
            if not f.get(k):
                break
        else:
            cont = False
        if cont:
            continue

        has_query = True
        ftype = f["ft"]
        field = f["ff"]
        operator = f["fo"]
        value = f["fv"]
        case = f.get("fc", False) and True

        if operator == "contain" and case:
            param = "__contains"
        elif operator == "contain" and not case:
            param = "__icontains"
        elif operator == "regexp" and case:
            param = "__regex"
        elif operator == "regexp" and not case:
            param = "__iregex"
        elif operator == "equal" and case:
            param = "__exact"
        elif operator == "equal" and not case:
            param = "__iexact"
        else:
            raise Exception(f"Unknown operation {operator}")

        if field not in list(dict(FILTER_FIELDS).keys()):
            fields = list(dict(FILTER_FIELDS).keys())
            raise Exception(f"Invalid FILTER_FIELDS {field} / {fields}")

        if field == "doc":
            content_param = {"content" + param: value}
            title_param = {"title" + param: value}
            url_param = {"url" + param: value}
            qf = models.Q(**content_param) | models.Q(**title_param) | models.Q(**url_param)
        elif field in ("lto_url", "lto_txt", "lby_url", "lby_txt"):
            field, rel_field = field.split("_")
            subfield = "doc_to" if field == "lto" else "doc_from"
            field = "links_to" if field == "lto" else "linked_from"
            if rel_field == "url":
                key1 = f"{field}__{subfield}__url{param}"
                key2 = f"{field}__extern_url{param}"
                qf = models.Q(**{key1: value}) | models.Q(**{key2: value})
            else:
                key = f"{field}__text{param}"
                qf = models.Q(**{key: value})
        elif field == "tag":
            key = f"name{param}"
            _tags = Tag.objects.filter(**{key: value})
            tags = set()
            for tag in _tags:
                tags |= set(Tag.get_tree(tag))
            qf = models.Q(tags__in=tags)
        else:
            qparams = {field + param: value}
            qf = models.Q(**qparams)

        if ftype == "exc":
            qf = ~qf
        elif ftype == "inc":
            pass
        else:
            raise Exception(f"Query type {operator} not supported")

        logger.debug(f"filter {ftype} {qf}")
        results = results.filter(qf)

    tags = form.cleaned_data.get("tag", [])
    for tag in tags:
        results = results.filter(tags__in=Tag.get_tree(tag))

    doc_lang = form.cleaned_data.get("doc_lang")
    if doc_lang:
        results = results.filter(lang_iso_639_1=doc_lang)

    collection_id = form.cleaned_data.get("collection")
    if collection_id:
        collection = Collection.objects.get(id=collection_id)
        results = results.filter(collection=collection)

    if not stats_call:
        order_by = form.cleaned_data["order_by"]

        # Ensure a deterministic order by adding a secondary sort on "id"
        if getattr(settings, "TEST_MODE", False):
            order_by = list(order_by) + ["id"]

        results = results.order_by(*order_by).distinct()

    if not has_query and not tags:
        results = Document.objects.none()

    return has_query, results, query


def fallback_headline(doc):
    lines = doc.content.splitlines()
    if lines:
        return lines[0]
    return ""


def add_headlines(paginated, query):
    for res in paginated:
        # rebuild the headline using non-normalized content
        if query:
            rnd = uuid.uuid1().hex
            pg_headline = (
                Document.objects.w_content()
                .filter(id=res.id)
                .annotate(
                    headline=SearchHeadline(
                        "normalized_content",
                        query,
                        start_sel="s" + rnd,
                        stop_sel="e" + rnd,
                    )
                )
                .first()
            )

            # find the location of the headline in the normalized content
            headline = pg_headline.headline.replace("s" + rnd, "")
            headline = headline.replace("e" + rnd, "")

            if (
                headline not in res.normalized_content
                or "s" + rnd not in pg_headline.headline
                or "e" + rnd not in pg_headline.headline
            ):
                res.headline = fallback_headline(res)
                continue

            headline_idx = res.normalized_content.index(headline)
            src = pg_headline.headline
            dest = escape("")
            while src:
                txt, src = src.split("s" + rnd, 1)
                dest += escape(res.content[headline_idx : headline_idx + len(txt)])
                headline_idx += len(txt)

                match, src = src.split("e" + rnd, 1)
                dest += '<span class="res-highlight">'
                dest += escape(res.content[headline_idx : headline_idx + len(match)])
                headline_idx += len(match)
                dest += "</span>"

                if "s" + rnd not in src or "e" + rnd not in src:
                    dest += res.content[headline_idx : len(src)]
                    break
            res.headline = mark_safe(dest)  # nosec B308, B703 untrusted content is escaped above
        else:
            res.headline = fallback_headline(res)
    return paginated


class SearchView(UserView):
    template_name = "se/search.html"

    def _short_search_history(self):
        search_history = SearchHistory.objects.filter(user=self.request.user).order_by("-date")
        unique_history = []
        unique_ids = []

        for entry in search_history:
            query_key = (entry.query, entry.querystring, entry.tags)
            if query_key not in unique_history:
                unique_history.append(query_key)
                unique_ids.append(entry.id)
            if len(unique_history) >= settings.SOSSE_HOME_SEARCH_HISTORY_SIZE:
                break

        return SearchHistory.objects.filter(id__in=unique_ids).order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = []
        paginated = None
        q = None
        has_query = False

        form = SearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data["q"]
            SearchHistory.save_history(self.request, q)

            if q.strip():
                redirect_url = SearchEngine.should_redirect(q, self.request)

                if redirect_url:
                    raise RedirectException(redirect_url)

            has_query, results, query = get_documents_from_request(self.request, form)
            paginator = Paginator(results, form.cleaned_data["ps"])
            page_number = self.request.GET.get("p")
            paginated = paginator.get_page(page_number)
            paginated = add_headlines(paginated, query)
        else:
            form = SearchForm({})
            form.is_valid()

        sosse_langdetect_to_postgres = OrderedDict(
            sorted(
                settings.SOSSE_LANGDETECT_TO_POSTGRES.items(),
                key=lambda x: x[1]["name"],
            )
        )

        if paginated:
            for r in paginated:
                # Set default link target and source / archive link
                if form.cleaned_data["c"]:
                    r.link = r.get_absolute_url()
                    r.link_flag = ""
                    r.extra_link = r.url
                    r.extra_link_flag = extern_link_flags()
                else:
                    r.link = r.url
                    r.link_flag = extern_link_flags()
                    r.extra_link = r.get_absolute_url()
                    r.extra_link_flag = ""

                if r.has_thumbnail:
                    r.preview = f"{settings.SOSSE_THUMBNAILS_URL}{r.image_name()}.jpg"
                elif r.screenshot_count:
                    r.preview = f"{settings.SOSSE_SCREENSHOTS_URL}{r.image_name()}_0.{r.screenshot_format}"
                elif r.mimetype and r.mimetype.startswith("image/") and r.has_html_snapshot:
                    asset = HTMLAsset.objects.filter(url=r.url).first()
                    if asset:
                        preview_url = self.request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + asset.filename
                        r.preview = preview_url
                r.ordered_tags = r.tags.order_by("name")
                for tag in r.ordered_tags:
                    tag.href = add_query_param(self.request, "tag", str(tag.id))

        extra_link_txt = "archive"
        if form.cleaned_data["c"]:
            extra_link_txt = "source"

        tags = []
        for tag in form.cleaned_data["tag"]:
            tag.clear_href = remove_query_param(self.request, "tag", str(tag.id))
            tags.append(tag)

        home_entries = None
        if (not has_query or tags) and settings.SOSSE_BROWSABLE_HOME:
            home_entries = Document.objects.wo_content().filter(show_on_homepage=True, hidden=False)
            if tags:
                for tag in tags:
                    home_entries = home_entries.filter(tags__in=Tag.get_tree(tag))
                if not home_entries:
                    has_query = True
            home_entries = home_entries.order_by("title").distinct()

        search_history = None
        if (
            (not has_query or tags)
            and self.request.user.is_authenticated
            and settings.SOSSE_HOME_SEARCH_HISTORY_SIZE > 0
        ):
            search_history = self._short_search_history()
            for entry in search_history:
                if entry.tags:
                    _tags = []
                    for tag in entry.tags:
                        tag = Tag.objects.filter(pk=tag).first()
                        if tag:
                            _tags.append(tag)
                            tag.name = f"⭐ {tag.name}"
                    entry.tags = _tags

        context.update(self._get_pagination(paginated))
        return context | {
            "hide_title": True,
            "form": form,
            "results": results,
            "results_count": human_nb(len(results)),
            "paginated": paginated,
            "has_query": has_query,
            "home_entries": home_entries,
            "search_history": search_history,
            "q": q,
            "title": q,
            "sosse_langdetect_to_postgres": sosse_langdetect_to_postgres,
            "extra_link_txt": extra_link_txt,
            "FILTER_FIELDS": FILTER_FIELDS,
            "tags": tags,
            "clear_tags_href": remove_query_param(self.request, "tag"),
        }
