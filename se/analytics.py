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

from .models import WorkerStats
from .views import AdminView


class AnalyticsView(AdminView):
    template_name = "admin/analytics.html"
    permission_required = set()
    title = "Analytics"

    def get_context_data(self):
        context = super().get_context_data()
        if self.request.user.has_perm("se.view_crawlerstats"):
            context["crawlers_count"] = WorkerStats.objects.count()
        return context
