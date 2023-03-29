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

from django.shortcuts import get_object_or_404, reverse
from django.utils.html import format_html
from urllib.parse import unquote

from .models import Document, CrawlPolicy, sanitize_url
from .utils import reverse_no_escape


def get_document(url):
    # re-establish double //
    scheme, url = url.split('/', 1)
    if url[0] != '/':
        url = '/' + url
    url = scheme + '/' + url
    url = sanitize_url(url, True, True)
    return get_object_or_404(Document, url=url)


def get_context(doc):
    crawl_policy = CrawlPolicy.get_from_url(doc.url)
    title = doc.title or doc.url
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
        'head_title': title,
        'title': page_title,
        'favicon': favicon
    }
