# Copyright 2024 Laurent Defert
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
from urllib.parse import unquote

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .cached import get_cached_doc, get_context, url_from_request
from .html_asset import HTMLAsset
from .login import login_required
from .utils import mimetype_icon


@login_required
def download(request: HttpRequest) -> HttpResponse:
    doc = get_cached_doc(request, 'html')
    if isinstance(doc, HttpResponse):
        return doc

    url = url_from_request(request)
    asset = HTMLAsset.objects.filter(url=url).order_by('download_date').last()

    if not asset or not os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
        return redirect(doc.get_absolute_url())

    asset_path = settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename

    filename = url.rstrip('/').rsplit('/', 1)[1]
    filename = unquote(filename)
    if '.' in filename:
        filename = filename.rsplit('.', 1)[0]

    extension = asset.filename.rsplit('.', 1)[1]
    filename = f'{filename}.{extension}'

    context = get_context(doc, 'download', request)
    context.update({
        'url': request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + asset.filename,
        'filename': filename,
        'filesize': os.path.getsize(asset_path),
        'icon': mimetype_icon(doc.mimetype),
        'mimebase': doc.mimetype.split('/', 1)[0]
    })
    return render(request, 'se/download.html', context)
