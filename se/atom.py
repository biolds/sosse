# Copyright 2022-2024 Laurent Defert
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

from hashlib import md5
from lxml.etree import Element, tostring

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import reverse

from .forms import SearchForm
from .models import SearchEngine
from .search import get_documents_from_request
from .utils import reverse_no_escape


def elem(tag, text, **attr):
    e = Element(tag, **attr)
    if text is not None:
        e.text = text
    return e


def str_to_uuid(s):
    s = md5(s.encode('utf-8')).hexdigest()
    s = s[:8] + '-' + s[8:12] + '-' + s[12:16] + '-' + s[16:20] + '-' + s[20:]
    s = 'urn:uuid:' + s
    return s


def atom_is_allowed(request):
    if request.user.is_authenticated:
        return True

    if settings.SOSSE_ANONYMOUS_SEARCH:
        return True

    if settings.SOSSE_ATOM_ACCESS_TOKEN:
        if request.GET.get('token') == settings.SOSSE_ATOM_ACCESS_TOKEN:
            return True

    return False


def atom(request):
    results = None
    q = None

    if not atom_is_allowed(request):
        raise PermissionDenied

    form = SearchForm(request.GET)
    if form.is_valid():
        q = form.cleaned_data['q']
        redirect_url = SearchEngine.should_redirect(q)
        if redirect_url:
            return HttpResponse('External search cannot be performed', content_type='text/plain', status=400)

        _, results, _ = get_documents_from_request(request, form)

        key = request.GET.get('s', '')
        if key.startswith('-'):
            key = key[1:]

        if key not in ('crawl_first', 'crawl_last'):
            key = 'crawl_first'

        param = {'%s__isnull' % key: True}
        results = results.exclude(**param)
        results = results.order_by('-' + key)

        base_url = request.META['REQUEST_SCHEME'] + '://' + request.META['HTTP_HOST']
        cached_page = request.GET.get('cached', '0')

        feed = Element('feed')
        feed.attrib['xmlns'] = 'http://www.w3.org/2005/Atom'
        feed.append(elem('title', f'SOSSE · {q}'))
        feed.append(elem('description', f'SOSSE search results for {q}'))
        url = base_url + reverse('search') + '?' + request.META['QUERY_STRING']
        feed.append(elem('link', None, href=url))
        if len(results):
            feed.append(elem('updated', getattr(results[0], key).isoformat()))
        feed_id = 'SOSSE' + request.META['QUERY_STRING']
        feed.append(elem('id', str_to_uuid(feed_id)))
        feed.append(elem('icon', base_url + settings.STATIC_URL + 'logo.svg'))

        for doc in results[:settings.SOSSE_ATOM_FEED_SIZE]:
            entry = Element('entry')
            entry.append(elem('title', doc.title))
            if cached_page == '0':
                url = doc.url
            else:
                url = base_url + reverse_no_escape('www', args=[doc.url])
            entry.append(elem('link', None, href=url))
            entry.append(elem('id', str_to_uuid(url)))
            entry.append(elem('updated', getattr(doc, key).isoformat()))

            content = ''
            lines = doc.content.splitlines()
            if lines:
                content = '\n'.join(lines[:5])
            entry.append(elem('summary', content))
            feed.append(entry)

        return HttpResponse(tostring(feed, pretty_print=True), content_type='text/plain')

    return HttpResponse('Invalid query parameters', content_type='text/plain', status=400)
