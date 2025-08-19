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

import logging
import os
import signal
import threading
from datetime import timedelta
from hashlib import md5
from multiprocessing import Process, cpu_count
from time import sleep
from traceback import format_exc

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.timezone import now

from ...browser_chromium import BrowserChromium
from ...browser_firefox import BrowserFirefox
from ...collection import Collection
from ...document import Document
from ...models import MINUTELY, CrawlerStats, WorkerStats

crawl_logger = logging.getLogger("crawler")
wake_event = None


class Command(BaseCommand):
    help = "Crawl web pages."
    doc = """This command starts one or multiple crawlers, depending on the :ref:`crawler count <conf_option_crawler_count>` option set in the :doc:`configuration file <config_file>`."""

    def __del__(self):
        BrowserChromium.destroy()
        BrowserFirefox.destroy()

    def add_arguments(self, parser):
        parser.add_argument(
            "--one-shot",
            action="store_true",
            help="Quit when the queue is empty.",
        )
        parser.add_argument(
            "--collection",
            type=int,
            help="Collection ID to use for URLs added to the queue.",
        )
        parser.add_argument(
            "urls",
            nargs="*",
            type=str,
            help="Optionnal list of URLs to add to the crawler queue.",
        )

    @staticmethod
    def next_stat():
        last = CrawlerStats.objects.filter(freq=MINUTELY).order_by("t").last()

        if last:
            next_stat = last.t + timedelta(minutes=1)
        else:
            next_stat = now()
        return next_stat

    @staticmethod
    def next_doc():
        doc = (
            Document.objects.wo_content()
            .filter(crawl_next__isnull=False, worker_no__isnull=True)
            .order_by("crawl_next")
            .first()
        )
        next_doc = None
        if doc:
            next_doc = (doc.crawl_next - now()).total_seconds()
        return next_doc

    @staticmethod
    def sleep_time(worker_no):
        next_doc = Command.next_doc()
        next_stat = None
        if worker_no == 0:
            next_stat = Command.next_stat()
            next_stat = (next_stat - now()).total_seconds()
            if next_doc:
                return min(next_doc, next_stat)
            return next_stat

        if next_doc:
            return next_doc
        return 60 * 60

    @staticmethod
    def wake_up_handler(signum, frame):
        crawl_logger.debug("Signal received, waking up worker")
        global wake_event
        wake_event.set()

    @staticmethod
    def process(worker_no, options):
        crawl_logger.info(f"Crawler {worker_no} initializing")
        connection.close()
        connection.connect()

        global wake_event
        wake_event = threading.Event()
        signal.signal(signal.SIGUSR1, Command.wake_up_handler)

        BrowserFirefox._worker_no = worker_no
        BrowserChromium._worker_no = worker_no
        base_dir = settings.SOSSE_TMP_DL_DIR + "/chromium/" + str(worker_no)
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        # change cwd to Chromium's because it downloads directory (while Firefox has an option for target dir)
        os.chdir(base_dir)

        crawl_logger.info(f"Crawler {worker_no} starting")

        worker_stats = WorkerStats.get_worker(worker_no)
        next_stat = Command.next_stat()

        while True:
            if worker_no == 0:
                t = now()
                if next_stat <= t:
                    CrawlerStats.create(t)
                    next_stat = Command.next_stat()

            worker_stats.refresh_from_db()
            try:
                if worker_stats.state == "paused" or not Document.crawl(worker_no):
                    if worker_stats.state != "paused" and options["one_shot"]:
                        return
                    if worker_stats.state == "running":
                        worker_stats.update_state("idle")

                    if BrowserChromium.inited or BrowserFirefox.inited:
                        next_doc = Command.next_doc()
                        if next_doc is None or next_doc > settings.SOSSE_BROWSER_IDLE_EXIT_TIME:
                            BrowserChromium.destroy()
                            BrowserFirefox.destroy()

                    if worker_stats.state == "paused" and worker_no == 0:
                        next_stat = Command.next_stat()
                        sleep_time = (next_stat - now()).total_seconds()
                        crawl_logger.debug(f"Sleeping for {sleep_time} seconds")
                    elif worker_stats.state == "paused" and worker_no != 0:
                        sleep_time = None
                        crawl_logger.debug("Worker paused")
                    else:
                        sleep_time = Command.sleep_time(worker_no)
                        crawl_logger.debug(f"Sleeping for {sleep_time} seconds")

                    wake_event.clear()
                    woke_up = wake_event.wait(timeout=sleep_time)
                    if woke_up:
                        crawl_logger.debug(f"Worker {worker_no} woke up")

            except Exception:
                crawl_logger.error(format_exc())
                sleep(5)

    def handle(self, *args, **options):
        # Validate that urls and collection parameters are both provided or both omitted
        if options["urls"] and not options["collection"]:
            self.stderr.write("Error: --collection parameter is required when URLs are provided.")
            return
        if options["collection"] and not options["urls"]:
            self.stderr.write("Error: URLs must be provided when --collection parameter is used.")
            return

        Document.objects.wo_content().exclude(worker_no=None).update(worker_no=None)
        error_msg = "Worker was killed"
        error_hash = md5(error_msg.encode("utf-8"), usedforsecurity=False).hexdigest()
        Document.objects.wo_content().filter(retries__gt=settings.SOSSE_WORKER_CRASH_RETRY).update(
            error=error_msg, error_hash=error_hash
        )

        Collection.create_default()

        for url in options["urls"]:
            try:
                collection = Collection.objects.get(id=options["collection"])
            except Collection.DoesNotExist:
                self.stderr.write(f"Collection with ID {options['collection']} does not exist.")
                return
            Document.manual_queue(url, collection, False)

        worker_count = settings.SOSSE_CRAWLER_COUNT
        if worker_count is None:
            worker_count = int(cpu_count() / 2)
            worker_count = max(worker_count, 1)

        WorkerStats.objects.filter(worker_no__gte=worker_count).delete()
        crawl_logger.info(f"Starting {worker_count} crawlers")

        workers = []
        for crawler_no in range(worker_count):
            p = Process(target=self.process, args=(crawler_no, options))
            p.start()
            workers.append(p)

        crawl_logger.info("Crawlers started")
        for worker in workers:
            worker.join()

        crawl_logger.info("Crawlers finished")
