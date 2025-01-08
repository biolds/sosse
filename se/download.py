# Copyright 2024-2025 Laurent Defert
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
from django.views.generic import TemplateView

from .archive import ArchiveMixin
from .html_asset import HTMLAsset
from .utils import mimetype_icon
from .views import RedirectException


class DownloadView(ArchiveMixin, TemplateView):
    template_name = "se/download.html"
    view_name = "download"

    def get_context_data(self, *args, **kwargs) -> dict:
        url = self._url_from_request()
        asset = HTMLAsset.objects.filter(url=url).order_by("download_date").last()

        if not asset or not os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
            raise RedirectException(self.doc.get_absolute_url())

        asset_path = settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename

        filename = url.rstrip("/").rsplit("/", 1)[1]
        filename = unquote(filename)
        if "." in filename:
            filename = filename.rsplit(".", 1)[0]

        extension = asset.filename.rsplit(".", 1)[1]
        filename = f"{filename}.{extension}"

        context = super().get_context_data()
        return context | {
            "url": self.request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + asset.filename,
            "filename": filename,
            "filesize": os.path.getsize(asset_path),
            "icon": mimetype_icon(self.doc.mimetype),
            "mimebase": self.doc.mimetype.split("/", 1)[0],
        }
