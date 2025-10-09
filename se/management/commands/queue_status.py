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

import json

from django.core.management.base import BaseCommand
from django.db import models
from django.utils.timezone import now

from ...document import Document
from ...models import WorkerStats


class Command(BaseCommand):
    help = "Display the crawling queue status."

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text or json)")

    def handle(self, *args, **options):
        current_time = now()

        processing_count = Document.objects.wo_content().filter(worker_no__isnull=False).count()
        queue_new_count = Document.objects.wo_content().filter(crawl_last__isnull=True, worker_no__isnull=True).count()
        queue_recurring_count = (
            Document.objects.wo_content()
            .filter(
                crawl_last__isnull=False, crawl_next__isnull=False, crawl_next__lte=current_time, worker_no__isnull=True
            )
            .count()
        )

        queue_pending_count = (
            Document.objects.wo_content()
            .filter(models.Q(crawl_last__isnull=True) | models.Q(crawl_next__lte=current_time), worker_no__isnull=True)
            .count()
        )

        workers = WorkerStats.live_state()
        worker_count = workers.count()

        processing_docs = (
            Document.objects.wo_content().filter(worker_no__isnull=False).select_related().order_by("worker_no")
        )

        if options["format"] == "json":
            workers_data = []
            for worker in workers:
                worker_data = {
                    "worker_no": worker.worker_no,
                    "pid": worker.pid if worker.pid != "-" else None,
                    "state": worker.state,
                    "doc_processed": worker.doc_processed,
                    "current_url": None,
                }

                # Chercher le document en cours pour ce worker
                current_doc = processing_docs.filter(worker_no=worker.worker_no).first()
                if current_doc:
                    worker_data["current_url"] = current_doc.url

                workers_data.append(worker_data)

            result = {
                "timestamp": current_time.isoformat(),
                "queue": {
                    "processing": processing_count,
                    "new": queue_new_count,
                    "recurring": queue_recurring_count,
                    "total_pending": queue_pending_count,
                },
                "workers": {"count": worker_count, "details": workers_data},
            }

            self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            self.stdout.write(self.style.SUCCESS("=== Crawling Queue Status ==="))
            self.stdout.write(f"Timestamp: {current_time}")
            self.stdout.write("")

            self.stdout.write(self.style.WARNING("Queue:"))
            self.stdout.write(f"  Documents being processed: {processing_count}")
            self.stdout.write(f"  New documents pending: {queue_new_count}")
            self.stdout.write(f"  Recurring documents: {queue_recurring_count}")
            self.stdout.write(f"  Total documents in queue: {queue_pending_count}")
            self.stdout.write("")

            self.stdout.write(self.style.WARNING(f"Workers ({worker_count} total):"))

            if workers:
                for worker in workers:
                    state_color = (
                        self.style.SUCCESS
                        if worker.state == "running"
                        else (self.style.WARNING if worker.state == "idle" else self.style.ERROR)
                    )

                    self.stdout.write(f"  Worker {worker.worker_no}:")
                    self.stdout.write(f"    PID: {worker.pid}")
                    self.stdout.write(f"    State: {state_color(worker.state)}")
                    self.stdout.write(f"    Documents processed: {worker.doc_processed}")

                    # Display current processing URL
                    current_doc = processing_docs.filter(worker_no=worker.worker_no).first()
                    if current_doc:
                        self.stdout.write(f"    Current URL: {current_doc.url}")
                    else:
                        self.stdout.write("    Current URL: None")
                    self.stdout.write("")
            else:
                self.stdout.write("  No active workers")
