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

from django.conf import settings
from django.views.generic import TemplateView

from .archive import ArchiveMixin


class ScreenshotView(ArchiveMixin, TemplateView):
    template_name = "se/embed.html"
    view_name = "screenshot"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        return context | {
            "url": self.request.build_absolute_uri("/screenshot_full/") + self._url_from_request(),
            "allow_scripts": True,
        }


class ScreenshotFullView(ArchiveMixin, TemplateView):
    template_name = "se/screenshot_full.html"
    view_name = "screenshot_full"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        return context | {
            "screenshot": settings.SOSSE_SCREENSHOTS_URL + "/" + self.doc.image_name(),
            "screenshot_size": self.doc.screenshot_size.split("x"),
            "screenshot_format": self.doc.screenshot_format,
            "screenshot_mime": ("image/png" if self.doc.screenshot_format == "png" else "image/jpeg"),
            "links": self.doc.links_to.filter(screen_pos__isnull=False).order_by("link_no"),
            "screens": range(self.doc.screenshot_count),
        }
