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
from django.shortcuts import render

from .browser import SeleniumBrowser
from .cached import get_document, get_context, unknown_url_view
from .login import login_required
from .utils import reverse_no_escape


@login_required
def screenshot(request):
    doc = get_document(request)
    if doc is None:
        return unknown_url_view(request)

    base_dir, filename = SeleniumBrowser.screenshot_name(doc.url)

    context = get_context(doc)
    context.update({
        'screenshot': settings.SOSSE_SCREENSHOTS_URL + '/' + base_dir + '/' + filename,
        'screenshot_size': doc.screenshot_size.split('x'),
        'screenshot_format': doc.screenshot_format,
        'screenshot_mime': 'image/png' if doc.screenshot_format == 'png' else 'image/jpeg',
        'other_links': [{
            'href': reverse_no_escape('www', args=[doc.url]),
            'text': 'Text version',
        }, {
            'href': reverse_no_escape('words', args=[doc.url]),
            'text': 'Words weight',
        }],
        'links': doc.links_to.filter(screen_pos__isnull=False).order_by('link_no'),
        'screens': range(doc.screenshot_count or 0)
    })
    return render(request, 'se/screenshot.html', context)
