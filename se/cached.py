# Copyright 2022-2023 Laurent Defert
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

from django.shortcuts import redirect, render, reverse
from django.utils.html import format_html

from .models import Document, CrawlPolicy, sanitize_url
from .utils import url_beautify, reverse_no_escape


def url_from_request(request):
    # Keep the url with parameters
    url = request.META['REQUEST_URI'].split('/', 2)[-1]

    # re-establish double //
    scheme, url = url.split('/', 1)
    if url[0] != '/':
        url = '/' + url
    url = scheme + '/' + url

    url = urlparse(url)
    url = url._replace(netloc=unquote(url.netloc))
    url = url.geturl()
    return sanitize_url(url, True, True)


def get_document(request):
    url = url_from_request(request)
    return Document.objects.filter(url=url).first()


def get_context(doc):
    crawl_policy = CrawlPolicy.get_from_url(doc.url)
    beautified_url = url_beautify(doc.url)
    title = doc.title or beautified_url
    page_title = None
    favicon = None
    if doc.favicon and not doc.favicon.missing:
        favicon = reverse('favicon', args=(doc.favicon.id,))
        page_title = format_html('<img src="{}" style="height: 32px; width: 32px; vertical-align: bottom" alt="icon"> {}', favicon, title)
    else:
        page_title = title

    return {
        'crawl_policy': crawl_policy,
        'doc': doc,
        'www_redirect_url': doc.redirect_url and reverse_no_escape('www', args=[doc.redirect_url]),
        'head_title': title,
        'title': page_title,
        'beautified_url': beautified_url,
        'favicon': favicon
    }


def unknown_url_view(request):
    url = url_from_request(request)
    beautified_url = url_beautify(url)
    context = {
        'url': url,
        'title': beautified_url,
        'beautified_url': beautified_url,
        'crawl_policy': CrawlPolicy.get_from_url(url),
    }
    return render(request, 'se/unknown_url.html', context)


def cache_redirect(request):
    doc = get_document(request)
    if doc:
        return redirect(doc.get_absolute_url())
    url = url_from_request(request)
    return unknown_url_view(request, url)
