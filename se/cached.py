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

from django.conf import settings
from django.shortcuts import redirect, render, reverse
from django.utils.html import format_html

from .document import Document, extern_link_flags
from .forms import SearchForm
from .models import CrawlPolicy
from .online import online_status
from .url import sanitize_url, url_beautify
from .utils import reverse_no_escape


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
    return sanitize_url(url)


def get_cached_doc(request, view_name):
    doc = get_document(request)
    if doc is None:
        return unknown_url_view(request)
    if settings.SOSSE_CACHE_FOLLOWS_REDIRECT and doc.redirect_url:
        new_doc = Document.objects.filter(url=doc.redirect_url).first()
        if new_doc:
            return redirect(new_doc.get_absolute_url())
        return redirect(reverse_no_escape(view_name, args=[doc.redirect_url]))
    return doc


def get_document(request):
    url = url_from_request(request)
    return Document.objects.filter(url=url).first()


def get_context(doc, view_name, request):
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

    other_links = [{
        'href': reverse_no_escape('www', args=[doc.url]),
        'text': 'Text',
        'text_icon': '✏️',
        'name': 'www'
    }]
    if doc.has_html_snapshot:
        other_links.append({
            'href': reverse_no_escape('html', args=[doc.url]),
            'text': 'HTML',
            'text_icon': '🔖',
            'name': 'html'
        })
    if doc.screenshot_count:
        other_links.append({
            'href': reverse_no_escape('screenshot', args=[doc.url]),
            'text': 'Screenshot',
            'text_icon': '📷',
            'name': 'screenshot'
        })
    other_links.append({
        'href': reverse_no_escape('words', args=[doc.url]),
        'text': 'Words weight',
        'text_icon': '📚',
        'name': 'words'
    })

    return {
        'crawl_policy': crawl_policy,
        'doc': doc,
        'www_redirect_url': doc.redirect_url and reverse_no_escape('cache', args=[doc.redirect_url]),
        'head_title': title,
        'title': page_title,
        'beautified_url': beautified_url,
        'favicon': favicon,
        'other_links': other_links,
        'show_search_input': True,
        'search_form': SearchForm({}),
        'view_name': view_name,
        'settings': settings,
        'online_status': online_status(request)
    }


def unknown_url_view(request):
    url = url_from_request(request)
    beautified_url = url_beautify(url)
    context = {
        'url': url,
        'title': beautified_url,
        'beautified_url': beautified_url,
        'crawl_policy': CrawlPolicy.get_from_url(url),
        'extern_link_flags': extern_link_flags,
        'search_form': SearchForm({}),
        'online_status': online_status(request)
    }
    return render(request, 'se/unknown_url.html', context)


def cache_redirect(request):
    doc = get_document(request)
    if doc:
        return redirect(doc.get_absolute_url())
    return unknown_url_view(request)
