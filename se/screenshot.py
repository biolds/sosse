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

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from .cached import get_cached_doc, get_context, url_from_request
from .login import login_required


@login_required
def screenshot(request):
    doc = get_cached_doc(request, 'screenshot')
    if isinstance(doc, HttpResponse):
        return doc

    context = get_context(doc, 'screenshot', request)
    context.update({
        'url': request.build_absolute_uri('/screenshot_full/') + url_from_request(request)
    })
    return render(request, 'se/embed.html', context)


@login_required
def screenshot_full(request):
    doc = get_cached_doc(request, 'screenshot')
    if isinstance(doc, HttpResponse):
        return doc

    context = get_context(doc, 'screenshot', request)
    context.update({
        'screenshot': settings.SOSSE_SCREENSHOTS_URL + '/' + doc.image_name(),
        'screenshot_size': doc.screenshot_size.split('x'),
        'screenshot_format': doc.screenshot_format,
        'screenshot_mime': 'image/png' if doc.screenshot_format == 'png' else 'image/jpeg',
        'links': doc.links_to.filter(screen_pos__isnull=False).order_by('link_no'),
        'screens': range(doc.screenshot_count)
    })
    return render(request, 'se/screenshot_full.html', context)
