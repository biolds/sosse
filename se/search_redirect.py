# Copyright 2025 Laurent Defert
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

from urllib.parse import quote_plus

from django.conf import settings
from django.views.generic import TemplateView

from .login import SosseLoginRequiredMixin


class SearchRedirectView(SosseLoginRequiredMixin, TemplateView):
    template_name = "se/search_redirect.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context | {
            "url": self.request.build_absolute_uri("/"),
            "q": quote_plus(self.request.GET.get("q", "")),
            "settings": settings,
        }
