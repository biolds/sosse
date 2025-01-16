# Copyright 2022-2025 Laurent Defert
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
from django.views.generic import TemplateView

from .archive import ArchiveMixin
from .crawl_policy import CrawlPolicy
from .html_asset import HTMLAsset
from .views import RedirectException, UserView


class HTMLView(ArchiveMixin, TemplateView):
    template_name = "se/embed.html"
    view_name = "html"

    def get_context_data(self, *args, **kwargs):
        if not self.doc.mimetype or not self.doc.mimetype.startswith("text/"):
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

    def get_context_data(self, crawl_policy, method, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if method == "mime":
            method = "mimetype"
        elif method == "element":
            method = "target element"
        crawl_policy = CrawlPolicy.objects.filter(id=crawl_policy).first()
        return context | {"crawl_policy": crawl_policy, "method": method}
