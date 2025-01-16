# Copyright 2025 Laurent Defert
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

from django.db import models
from django.utils.timezone import now

from .crawlers import CrawlersOperationMixin
from .document import Document
from .models import WorkerStats
from .utils import human_dt
from .views import AdminView


class CrawlQueueContentView(AdminView):
    title = "Crawl queue"
    template_name = "admin/crawl_queue_content.html"
    permission_required = "se.view_crawlerstats"
    admin_site = None

    def __init__(self, *args, **kwargs):
        self.admin_site = kwargs.pop("admin_site")
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queue_new_count = Document.objects.filter(crawl_last__isnull=True).count()
        queue_recurring_count = Document.objects.filter(crawl_last__isnull=False, crawl_next__isnull=False).count()
        queue_pending_count = Document.objects.filter(
            models.Q(crawl_last__isnull=True) | models.Q(crawl_next__lte=now())
        ).count()

        QUEUE_SIZE = 10
        queue = list(Document.objects.filter(worker_no__isnull=False).order_by("id")[:QUEUE_SIZE])
        if len(queue) < QUEUE_SIZE:
            queue = queue + list(
                Document.objects.filter(crawl_last__isnull=True)
                .exclude(id__in=[q.pk for q in queue])
                .order_by("id")[:QUEUE_SIZE]
            )
        if len(queue) < QUEUE_SIZE:
            queue = queue + list(
                Document.objects.filter(crawl_last__isnull=False, crawl_next__isnull=False)
                .exclude(id__in=[q.pk for q in queue])
                .order_by("crawl_next", "id")[: QUEUE_SIZE - len(queue)]
            )
        for doc in queue:
            doc.pending = True

        queue.reverse()

        history = list(Document.objects.filter(crawl_last__isnull=False).order_by("-crawl_last")[:QUEUE_SIZE])

        for doc in queue:
            if doc in history:
                history.remove(doc)

        for doc in history:
            doc.in_history = True
        queue = queue + history

        for doc in queue:
            if doc.crawl_next:
                doc.crawl_next_human = human_dt(doc.crawl_next, True)
            if doc.crawl_last:
                doc.crawl_last_human = human_dt(doc.crawl_last, True)

        return (
            context
            | dict(self.admin_site.each_context(self.request))
            | {
                "pause": WorkerStats.objects.filter(state="paused").count() == 0,
                "queue": queue,
                "queue_new_count": queue_new_count,
                "queue_recurring_count": queue_recurring_count,
                "queue_pending_count": queue_pending_count,
                "now": now(),
            }
        )


class CrawlQueueView(CrawlersOperationMixin, CrawlQueueContentView):
    template_name = "admin/crawl_queue.html"
