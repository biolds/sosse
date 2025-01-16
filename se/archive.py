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

from urllib.parse import unquote, urlparse

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render, reverse
from django.utils.html import format_html
from django.views.generic import View

from .crawl_policy import CrawlPolicy
from .document import Document, extern_link_flags
from .login import LoginRequiredMixin
from .online import online_status
from .search_form import SearchForm
from .url import sanitize_url, url_beautify
from .utils import reverse_no_escape
from .views import RedirectException, RedirectMixin


class ArchiveMixin(RedirectMixin, LoginRequiredMixin):
    view_name = None

    def _url_from_request(self):
        # Keep the url with parameters
        url = self.request.META["REQUEST_URI"].split("/", 2)[-1]

        # re-establish double //
        scheme, url = url.split("/", 1)
        if url[0] != "/":
            url = "/" + url
        url = scheme + "/" + url

        url = urlparse(url)
        url = url._replace(netloc=unquote(url.netloc))
        url = url.geturl()
        return sanitize_url(url)

    def _get_archive_doc(self):
        doc = self._get_document()
        if doc is None:
            return self._unknown_url_view()
        if settings.SOSSE_ARCHIVE_FOLLOWS_REDIRECT and doc.redirect_url:
            new_doc = Document.objects.filter(url=doc.redirect_url).first()
            if new_doc:
                raise RedirectException(new_doc.get_absolute_url())
            raise RedirectException(reverse_no_escape(self.view_name, args=[doc.redirect_url]))
        return doc

    def _get_document(self):
        url = self._url_from_request()
        return Document.objects.filter(url=url).first()

    def get_context_data(self):
        context = super().get_context_data()
        crawl_policy = CrawlPolicy.get_from_url(self.doc.url)
        beautified_url = url_beautify(self.doc.url)
        title = self.doc.title or beautified_url
        page_title = None
        favicon = None
        if self.doc.favicon and not self.doc.favicon.missing:
            favicon = reverse("favicon", args=(self.doc.favicon.id,))
            page_title = format_html(
                '<img src="{}" style="height: 32px; width: 32px; vertical-align: bottom" alt="icon"> {}',
                favicon,
                title,
            )
        else:
            page_title = title

        other_links = []
        if self.doc.mimetype and self.doc.mimetype.startswith("text/"):
            other_links = [
                {
                    "href": reverse_no_escape("www", args=[self.doc.url]),
                    "text": "Text",
                    "text_icon": "✏️",
                    "name": "www",
                }
            ]
            if self.doc.has_html_snapshot:
                other_links.append(
                    {
                        "href": reverse_no_escape("html", args=[self.doc.url]),
                        "text": "HTML",
                        "text_icon": "🔖",
                        "name": "html",
                    }
                )
            if self.doc.screenshot_count:
                other_links.append(
                    {
                        "href": reverse_no_escape("screenshot", args=[self.doc.url]),
                        "text": "Screenshot",
                        "text_icon": "📷",
                        "name": "screenshot",
                    }
                )
        else:
            if self.doc.has_html_snapshot:
                other_links = [
                    {
                        "href": reverse_no_escape("download", args=[self.doc.url]),
                        "text": "Download",
                        "text_icon": "📂 ",
                        "name": "download",
                    }
                ]

        other_links.append(
            {
                "href": reverse_no_escape("words", args=[self.doc.url]),
                "text": "Words weight",
                "text_icon": "📚",
                "name": "words",
            }
        )

        return context | {
            "crawl_policy": crawl_policy,
            "doc": self.doc,
            "www_redirect_url": self.doc.redirect_url and reverse_no_escape("archive", args=[self.doc.redirect_url]),
            "head_title": title,
            "title": page_title,
            "beautified_url": beautified_url,
            "favicon": favicon,
            "other_links": other_links,
            "show_search_input": True,
            "search_form": SearchForm({}),
            "view_name": self.view_name,
            "settings": settings,
            "online_status": online_status(self.request),
        }

    def _unknown_url_view(self):
        url = self._url_from_request()
        beautified_url = url_beautify(url)
        context = {
            "url": url,
            "title": beautified_url,
            "beautified_url": beautified_url,
            "crawl_policy": CrawlPolicy.get_from_url(url),
            "extern_link_flags": extern_link_flags,
            "search_form": SearchForm({}),
            "online_status": online_status(self.request),
        }
        return render(self.request, "se/unknown_url.html", context)

    def get(self, request):
        if self.view_name is None:
            raise Exception("view_name must be overwritten")
        doc = self._get_archive_doc()
        if isinstance(doc, HttpResponse):
            return doc
        self.doc = doc
        return super().get(request)


class ArchiveRedirectView(ArchiveMixin, View):
    def get(self, request):
        doc = self._get_document()
        if doc:
            return redirect(doc.get_absolute_url())
        return self._unknown_url_view()
