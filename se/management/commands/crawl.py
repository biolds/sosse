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

from ...browser import ChromiumBrowser, FirefoxBrowser
from ...models import CrawlerStats, Document, CrawlPolicy, MINUTELY, WorkerStats

crawl_logger = logging.getLogger('crawler')


class Command(BaseCommand):
    help = 'Crawl web pages.'
    doc = '''This command starts one or multiple crawlers, depending on the :ref:`crawler count <conf_option_crawler_count>` option set in the :doc:`configuration file <config_file>`.'''

    def __del__(self):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='*', type=str, help='Optionnal list of URLs to add to the crawler queue.')

    @staticmethod
    def process(worker_no, options):
        try:
            crawl_logger.info('Crawler %i initializing' % worker_no)
            connection.close()
            connection.connect()

            FirefoxBrowser.worker_no = worker_no
            ChromiumBrowser.worker_no = worker_no
            base_dir = settings.SOSSE_TMP_DL_DIR + '/chromium/' + str(worker_no)
            if not os.path.isdir(base_dir):
                os.makedirs(base_dir)
            # change cwd to Chromium's because it downloads directory (while Firefox has an option for target dir)
            os.chdir(base_dir)

            crawl_logger.info('Crawler %i starting' % worker_no)

            if worker_no == 0:
                last = CrawlerStats.objects.filter(freq=MINUTELY).order_by('t').last()
                if last:
                    next_stat = last.t
                else:
                    next_stat = now()
                next_stat += timedelta(minutes=1)

            sleep_count = 0
            while True:
                if worker_no == 0:
                    t = now()
                    if next_stat < t:
                        CrawlerStats.create(t)
                        next_stat = t + timedelta(minutes=1)

                worker_stats = WorkerStats.get_worker(worker_no)

                if worker_stats.state == 'paused' or not Document.crawl(worker_no):
                    if worker_stats.state == 'running':
                        worker_stats.update_state('idle')
                    if sleep_count % 60 == 0:
                        crawl_logger.debug('%s %s...' % (worker_no, worker_stats.state.title()))
                    sleep_count += 1
                    if sleep_count > settings.SOSSE_BROWSER_IDLE_EXIT_TIME:
                        ChromiumBrowser.destroy()
                        FirefoxBrowser.destroy()
                    sleep(1)
                else:
                    sleep_count = 0

        except Exception:
            crawl_logger.error(format_exc())
            raise

    def handle(self, *args, **options):
        Document.objects.exclude(worker_no=None).update(worker_no=None)
        CrawlPolicy.create_default()

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
