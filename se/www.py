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

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.html import format_html

from .cached import get_cached_doc, get_context
from .login import login_required
from .models import Link


def get_content(doc):
    content = format_html('')
    content_pos = 0

    links = Link.objects.filter(doc_from=doc).order_by('link_no')
    links_count = Link.objects.filter(doc_from=doc).count()
    link_no = 0
    for line in doc.content.splitlines():
        while link_no < links_count and links[link_no].pos < content_pos + len(line):
            link = links[link_no]
            link_pos = link.pos - content_pos
            txt = line[:link_pos]
            if not link.in_nav:
                line = line[link_pos + len(link.text or ''):]
                content_pos += len(txt) + len(link.text or '')

            if link.doc_to:
                content += format_html('{} <a href="{}">{}</a>',
                                       txt,
                                       link.doc_to.get_absolute_url(),
                                       link.text or '<no text link>',
                                       link.doc_to.url)
            else:
                content += format_html('{} <a href="{}">🌍</a>',
                                       txt,
                                       link.text or '<no text link>',
                                       link.extern_url)
            link_no += 1

        content_pos += len(line) + 1  # +1 for the \n stripped by splitlines()
        content += format_html('{}<br/>', line)
    return content


@login_required
def www(request):
    doc = get_cached_doc(request, 'www')
    if isinstance(doc, HttpResponse):
        return doc

    context = get_context(doc, 'www', request)
    context['content'] = get_content(doc)
    return render(request, 'se/www.html', context)
