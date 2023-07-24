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

import os

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .cached import get_cached_doc, get_context, url_from_request
from .html_snapshot import HTMLSnapshot
from .login import login_required
from .utils import reverse_no_escape


@login_required
def html(request):
    doc = get_cached_doc(request, 'html')
    if isinstance(doc, HttpResponse):
        return doc

    page_file = HTMLSnapshot.html_filename(url_from_request(request), doc.content_hash, '.html')
    if not os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + page_file):
        return redirect(reverse_no_escape('www', args=(doc.url,)))

    context = get_context(doc, 'html')
    context['url'] = request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + page_file
    return render(request, 'se/embed.html', context)