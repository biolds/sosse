# Copyright 2022-2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import os

from django.conf import settings
from django.views.generic import TemplateView

from .archive import ArchiveMixin
from .collection import Collection
from .html_asset import HTMLAsset
from .views import RedirectException, UserView


class HTMLView(ArchiveMixin, TemplateView):
    template_name = "se/embed.html"
    view_name = "html"

    def get_context_data(self, *args, **kwargs):
        if not self.doc.content:
            raise RedirectException(self.doc.get_absolute_url())

        url = self._url_from_request()
        asset = HTMLAsset.objects.filter(url=url).order_by("download_date").last()

        if not asset or not os.path.exists(settings.SOSSE_HTML_SNAPSHOT_DIR + asset.filename):
            raise RedirectException(self.doc.get_absolute_url())

        context = super().get_context_data()
        return context | {
            "url": self.request.build_absolute_uri(settings.SOSSE_HTML_SNAPSHOT_URL) + asset.filename,
            "allow_scripts": False,
        }


class HTMLExcludedView(UserView):
    template_name = "se/html_excluded.html"

    def get_context_data(self, collection, method, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if method == "mime":
            method = "mimetype"
        elif method == "element":
            method = "target element"
        collection = Collection.objects.filter(id=collection).first()
        return context | {"collection": collection, "method": method}
