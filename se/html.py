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
from .html_asset import HTMLAsset
from .login import login_required
from .models import CrawlPolicy


@login_required
def html(request):
    doc = get_cached_doc(request, 'html')
    if isinstance(doc, HttpResponse):
        return doc

    url = url_from_request(request)
    asset = HTMLAsset.objects.filter(url=url).order_by('download_date').last()

    if not asset or not os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
        return redirect(doc.get_absolute_url())

    context = get_context(doc, 'html', request)
    context['url'] = request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + asset.filename
    return render(request, 'se/embed.html', context)


@login_required
def html_excluded(request, crawl_policy, method):
    if method == 'mime':
        method = 'mimetype'
    elif method == 'element':
        method = 'target element'
    crawl_policy = CrawlPolicy.objects.filter(id=crawl_policy).first()
    context = {
        'crawl_policy': crawl_policy,
        'method': method
    }
    return render(request, 'se/html_excluded.html', context)
