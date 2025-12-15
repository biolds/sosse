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

from django.conf import settings
from django.views.generic import TemplateView


class ConfigJsView(TemplateView):
    template_name = "se/config.js"
    content_type = "application/javascript"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context |= {
            "snapshot_url": settings.SOSSE_HTML_SNAPSHOT_URL,
            "anonymous_search": "true" if settings.SOSSE_ANONYMOUS_SEARCH else "false",
            "online_search_redirect": "true" if settings.SOSSE_ONLINE_SEARCH_REDIRECT else "false",
            "max_page_size": settings.SOSSE_MAX_PAGE_SIZE,
            "page_size": settings.REST_FRAMEWORK.get("PAGE_SIZE", 10),
            "csv_export": "true" if settings.SOSSE_CSV_EXPORT else "false",
            "crawl_status_autorefresh": settings.SOSSE_CRAWL_STATUS_AUTOREFRESH,
            "browsable_home": "true" if settings.SOSSE_BROWSABLE_HOME else "false",
            "links_no_referrer": "true" if settings.SOSSE_LINKS_NO_REFERRER else "false",
            "links_new_tab": "true" if settings.SOSSE_LINKS_NEW_TAB else "false",
        }
        return context
