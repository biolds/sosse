# Copyright 2022-2023 Laurent Defert
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

import logging
import os
from datetime import timedelta
from multiprocessing import cpu_count, Process
from time import sleep
from traceback import format_exc

from django.conf import settings
from django.db import connection
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...browser import Browser
from ...models import CrawlerStats, Document, CrawlPolicy, MINUTELY, WorkerStats

crawl_logger = logging.getLogger('crawler')


class Command(BaseCommand):
    help = 'Crawl web pages'

    def __del__(self):
        Browser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='*', type=str)

    @staticmethod
    def process(worker_no, options):
        try:
            crawl_logger.info('Crawler %i initializing' % worker_no)
            connection.close()
            connection.connect()

            base_dir = settings.SOSSE_TMP_DL_DIR + '/' + str(worker_no)
            if not os.path.isdir(base_dir):
                os.makedirs(base_dir)
            os.chdir(base_dir)

            for f in os.listdir(base_dir):
                os.unlink(f)

            Browser.init()
            crawl_logger.info('Crawler %i starting' % worker_no)
            worker_stats = WorkerStats.get_worker(worker_no)

            if worker_no == 0:
                last = CrawlerStats.objects.filter(freq=MINUTELY).order_by('t').last()
                if last:
                    next_stat = last.t
                else:
                    next_stat = now()
                next_stat += timedelta(minutes=1)

                sleep_count = 0
                while True:
                    t = now()
                    if next_stat < t:
                        if worker_no == 0:
                            CrawlerStats.create(t)
                        next_stat = t + timedelta(minutes=1)

                    paused = WorkerStats.get_worker(worker_no).state == 'paused'

                    if not paused and Document.crawl(worker_no):
                        if sleep_count != 0:
                            worker_stats.update_state(0)
                        sleep_count = 0
                    else:
                        if sleep_count == 0:
                            worker_stats.update_state(1)
                        if sleep_count % 60 == 0:
                            crawl_logger.debug('%s Idle...' % worker_no)
                        sleep_count += 1
                        sleep(1)
        except Exception:
            crawl_logger.error(format_exc())
            raise

    def handle(self, *args, **options):
        Document.objects.exclude(worker_no=None).update(worker_no=None)
        CrawlPolicy.objects.get_or_create(url_regex='.*', defaults={'condition': CrawlPolicy.CRAWL_NEVER})  # mandatory default policy

        for url in options['urls']:
            Document.queue(url, None, 0)

        worker_count = settings.SOSSE_CRAWLER_COUNT
        if worker_count is None:
            worker_count = cpu_count()

        WorkerStats.objects.filter(worker_no__gte=worker_count).delete()
        crawl_logger.info('Starting %i crawlers' % worker_count)

        workers = []
        for crawler_no in range(worker_count):
            p = Process(target=self.process, args=(crawler_no, options))
            p.start()
            workers.append(p)
            sleep(5)

        crawl_logger.info('Crawlers started')
        for worker in workers:
            worker.join()

        crawl_logger.info('Crawlers finished')
