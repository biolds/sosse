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

from collections import OrderedDict
from dataclasses import dataclass
import json
from random import choice
from urllib.parse import urlparse, parse_qs, quote_plus

from django.conf import settings
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from .document import Document, extern_link_flags, remove_accent
from .forms import SearchForm, FILTER_FIELDS
from .login import login_required
from .online import online_status
from .models import FavIcon, SearchEngine, SearchHistory
from .search import add_headlines, get_documents_from_request
from .utils import human_nb


ANIMALS = "🦓🦬🦣🦒🦦🦥🦘🦌🐢🦝🦭🦫🐆🐅🦎🐍🐘🦙🐫🐪🐏🐐🦛🦏🐂🐃🐎🐑🐒🦇🐖🐄🐛🐝🦧🦍🐜🐞🐌🦋🦗🐨🐯🦁🐮🐰🐻🐻‍❄️🐼🐶🐱🐭🐹🐗🐴🐷🐣🐥🐺🦊🐔🐧🐦🐤🐋🐊🐸🐵🐡🐬🦈🐳🦐🦪🐠🐟🐙🦑🦞🦀🦅🕊🦃🐓🦉🦤🦢🦆🪶🦜🦚🦩🐩🐕‍🦮🐕🐁🐀🐇🐈🦔🦡🦨🐿"


def format_url(request, params):
    parsed_url = urlparse(request.get_full_path())
    query_string = parse_qs(parsed_url.query)
    for k, v in query_string.items():
        query_string[k] = v[0]

    for param in params.split("&"):
        val = None
        if "=" in param:
            key, val = param.split("=", 1)
        else:
            key = param

        if val:
            query_string[key] = val
        else:
            query_string.pop(key, None)

    qs = "&".join([f"{k}={v}" for k, v in query_string.items()])
    return parsed_url._replace(query=qs).geturl()


@dataclass
class RedirectException(Exception):
    url: str


class SosseMixin:
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except RedirectException as e:
            return redirect(e.url)


class UserView(SosseMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self, "title"):
            context["title"] = self.title
        animal = ""
        while not animal:
            # choice sometimes returns an empty string for an unknown reason
            animal = choice(ANIMALS)

        return context | {
            "settings": settings,
            "animal": animal,
            "online_status": online_status(self.request),
        }

    def _get_pagination(self, paginated):
        context = {}
        if paginated and paginated.has_previous():
            context.update(
                {
                    "page_first": format_url(self.request, "p="),
                    "page_previous": format_url(self.request, f"p={paginated.previous_page_number()}"),
                }
            )
        if paginated and paginated.has_next():
            context.update(
                {
                    "page_next": format_url(self.request, f"p={paginated.next_page_number()}"),
                    "page_last": format_url(self.request, f"p={paginated.paginator.num_pages}"),
                }
            )
        return context


@method_decorator(login_required, name="dispatch")
class SearchView(UserView):
    template_name = "se/index.html"

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

        extra_link_txt = "cached"
        if form.cleaned_data["c"]:
            extra_link_txt = "source"

        home_entries = None
        if not has_query and settings.SOSSE_BROWSABLE_HOME:
            home_entries = Document.objects.filter(show_on_homepage=True).order_by("title")

        context.update(self._get_pagination(paginated))
        return context | {
            "hide_title": True,
            "form": form,
            "results": results,
            "results_count": human_nb(len(results)),
            "paginated": paginated,
            "has_query": has_query,
            "home_entries": home_entries,
            "q": q,
            "title": q,
            "sosse_langdetect_to_postgres": sosse_langdetect_to_postgres,
            "extra_link_txt": extra_link_txt,
            "FILTER_FIELDS": FILTER_FIELDS,
        }


@method_decorator(login_required, name="dispatch")
class AboutView(UserView):
    template_name = "se/about.html"
    title = "About"


@method_decorator(login_required, name="dispatch")
class WordStatsView(View):
    def get(self, request):
        results = None
        form = SearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data["q"]
            q = remove_accent(q)
            _, doc_query, _ = get_documents_from_request(request, form, True)
            doc_query = doc_query.values("vector")

            # Hack to obtain final SQL query, as described there:
            # https://code.djangoproject.com/ticket/17741#comment:4
            sql, params = doc_query.query.sql_with_params()
            cursor = connection.cursor()
            cursor.execute("EXPLAIN " + sql, params)
            raw_query = cursor.db.ops.last_executed_query(cursor, sql, params)
            raw_query = raw_query[len("EXPLAIN ") :]

            results = Document.objects.raw(
                "SELECT 1 AS id, word, ndoc FROM ts_stat(%s) ORDER BY ndoc DESC, word ASC LIMIT 100",
                (raw_query,),
            )
            results = [
                (
                    e.word,
                    human_nb(e.ndoc),
                    format_url(request, f"q={q} {e.word}")[len("/word_stats") :],
                )
                for e in list(results)
            ]
            results = json.dumps(results)

        return HttpResponse(results, content_type="application/json")


@method_decorator(login_required, name="dispatch")
class PreferencesView(UserView):
    template_name = "se/prefs.html"
    title = "Preferences"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context | {"supported_langs": json.dumps(Document.get_supported_lang_dict())}


@method_decorator(login_required, name="dispatch")
class FavIconView(View):
    def get(self, request, favicon_id):
        fav = get_object_or_404(FavIcon, id=favicon_id)
        return HttpResponse(fav.content, content_type=fav.mimetype)


@method_decorator(login_required, name="dispatch")
class HistoryView(UserView):
    template_name = "se/history.html"
    title = "History"

    def dispatch(self, request, *args, **kwargs):
        # Require authentication whatever the value of SOSSE_ANONYMOUS_SEARCH
        if not request.user.is_authenticated:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_size = int(self.request.GET.get("ps", settings.SOSSE_DEFAULT_PAGE_SIZE))
        page_size = min(page_size, settings.SOSSE_MAX_PAGE_SIZE)

        history = SearchHistory.objects.filter(user=self.request.user).order_by("-date")
        paginator = Paginator(history, page_size)
        page_number = int(self.request.GET.get("p", 1))
        paginated = paginator.get_page(page_number)

        context["paginated"] = paginated
        context.update(self._get_pagination(paginated))
        return context

    def post(self, request):
        if "del_all" in self.request.POST:
            SearchHistory.objects.filter(user=self.request.user).delete()
        else:
            for key, val in self.request.POST.items():
                if key.startswith("del_"):
                    key = int(key[4:])
                    obj = SearchHistory.objects.filter(id=key, user=self.request.user).first()
                    if obj:
                        obj.delete()
        return super().get(request)


class OpensearchView(TemplateView):
    template_name = "se/opensearch.xml"
    content_type = "application/xml"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context | {"url": self.request.build_absolute_uri("/").rstrip("/")}


@method_decorator(login_required, name="dispatch")
class SearchRedirectView(TemplateView):
    template_name = "se/search_redirect.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context | {
            "url": self.request.build_absolute_uri("/"),
            "q": quote_plus(self.request.GET.get("q", "")),
            "settings": settings,
        }


@method_decorator(login_required, name="dispatch")
class StatisticsView(TemplateView):
    template_name = "admin/stats.html"
    extra_context = {"title": "Statistics"}

    def get(self, request):
        if not request.user.is_staff or not request.user.is_superuser:
            return redirect(reverse("search"))
        return super().get(request)


class SELoginView(LoginView):
    template_name = "admin/login.html"
