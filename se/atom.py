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

import os
from hashlib import md5

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic import View
from lxml.etree import (  # nosec B410, ignore Bandit warning because lxml is only used for XML generation
    Element,
    tostring,
)

from .html_asset import HTMLAsset
from .models import SearchEngine
from .search import get_documents_from_request
from .search_form import SearchForm
from .utils import reverse_no_escape


class AtomView(View):
    def _elem(self, tag, text, **attr):
        e = Element(tag, **attr)
        if text is not None:
            e.text = text
        return e

    def _str_to_uuid(self, s):
        s = md5(s.encode("utf-8"), usedforsecurity=False).hexdigest()
        s = s[:8] + "-" + s[8:12] + "-" + s[12:16] + "-" + s[16:20] + "-" + s[20:]
        s = "urn:uuid:" + s
        return s

    def _atom_is_allowed(self, request):
        if request.user.is_authenticated:
            return True

        if settings.SOSSE_ANONYMOUS_SEARCH:
            return True

        if settings.SOSSE_ATOM_ACCESS_TOKEN:
            if request.GET.get("token") == settings.SOSSE_ATOM_ACCESS_TOKEN:
                return True

        return False

    def get(self, request):
        results = None
        q = None

        if not self._atom_is_allowed(request):
            raise PermissionDenied

        form = SearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data["q"]
            redirect_url = SearchEngine.should_redirect(q)
            if redirect_url:
                return HttpResponse(
                    b"External search cannot be performed",
                    content_type="text/plain",
                    status=400,
                )

            _, results, _ = get_documents_from_request(request, form)

            sort_key = request.GET.get("s", "")
            if sort_key.startswith("-"):
                sort_key = sort_key[1:]

            if sort_key not in ("crawl_first", "crawl_last"):
                sort_key = "crawl_first"

            param = {f"{sort_key}__isnull": True}
            results = results.exclude(**param)
            results = results.order_by("-" + sort_key)

            base_url = request.META["REQUEST_SCHEME"] + "://" + request.META["HTTP_HOST"]
            archive_page = request.GET.get("archive", "0")

            feed = Element("feed")
            feed.attrib["xmlns"] = "http://www.w3.org/2005/Atom"
            feed.append(self._elem("title", f"SOSSE · {q}"))
            feed.append(self._elem("description", f"SOSSE search results for {q}"))
            url = base_url + reverse("search") + "?" + request.META["QUERY_STRING"]
            feed.append(self._elem("link", None, href=url))
            if len(results):
                feed.append(self._elem("updated", getattr(results[0], sort_key).isoformat()))
            feed_id = "SOSSE" + request.META["QUERY_STRING"]
            feed.append(self._elem("id", self._str_to_uuid(feed_id)))
            feed.append(self._elem("icon", base_url + settings.STATIC_URL + "logo.svg"))

            for doc in results[: settings.SOSSE_ATOM_FEED_SIZE]:
                entry = Element("entry")
                entry.append(self._elem("title", doc.title))
                if archive_page == "0":
                    url = doc.url
                else:
                    if settings.SOSSE_ATOM_ARCHIVE_BIN_PASSTHROUGH and (
                        not doc.mimetype or not doc.mimetype.startswith("text/")
                    ):
                        asset = HTMLAsset.objects.filter(url=doc.url).order_by("download_date").last()
                        if not asset or not os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
                            url = base_url + reverse_no_escape("www", args=[doc.url])
                        else:
                            url = request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + asset.filename
                    else:
                        if doc.mimetype.startswith("text/"):
                            view_name = "www"
                        else:
                            view_name = "download"
                        url = base_url + reverse_no_escape(view_name, args=[doc.url])
                entry.append(self._elem("link", None, href=url))

                sort_value = getattr(doc, sort_key)
                if sort_key in ("crawl_first", "crawl_last", "modified_date"):
                    sort_value = sort_value.isoformat()
                entry.append(self._elem("id", self._str_to_uuid(f"{url}-{sort_value}")))

                if sort_key in ("crawl_first", "crawl_last", "modified_date"):
                    entry.append(self._elem("updated", sort_value))

                content = ""
                lines = doc.content.splitlines()
                if lines:
                    content = "\n".join(lines[:5])
                entry.append(self._elem("summary", content))
                feed.append(entry)

            return HttpResponse(tostring(feed, pretty_print=True), content_type="text/plain")

        return HttpResponse(b"Invalid query parameters", content_type="text/plain", status=400)
