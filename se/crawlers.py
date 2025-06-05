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


class CrawlersOperationMixin:
    def get_permission_required(self):
        if self.request.method == "POST":
            return {"se.change_crawlerstats"}
        return super().get_permission_required()

    def post(self, request):
        if "pause" in request.POST:
            WorkerStats.objects.update(state="paused")
        if "resume" in request.POST:
            WorkerStats.objects.update(state="running")
            WorkerStats.wake_up()
        return self.get(request)


class CrawlersContentView(AdminView):
    template_name = "admin/crawlers_content.html"
    permission_required = "se.view_crawlerstats"
    admin_site = None

    def __init__(self, *args, **kwargs):
        self.admin_site = kwargs.pop("admin_site")
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        crawlers = WorkerStats.live_state()
        running_count = [c for c in crawlers if c.state != "exited"]
        return context | {
            "crawlers": WorkerStats.live_state(),
            "running_count": running_count,
            "pause": WorkerStats.objects.filter(state="paused").count() == 0,
        }


class CrawlersView(CrawlersOperationMixin, CrawlersContentView):
    title = "Crawlers"
    template_name = "admin/crawlers.html"
