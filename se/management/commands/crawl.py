import uuid
from datetime import datetime, timedelta
from multiprocessing import cpu_count, Process
from time import sleep

from django.db import connection
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from ...browser import Browser
from ...models import UrlQueue, Document, CrawlerStats


class Command(BaseCommand):
    help = 'Crawl web pages'

    def __del__(self):
        Browser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Exit when url queue is empty')
        parser.add_argument('--requeue', action='store_true', help='Exit when url queue is empty')
        parser.add_argument('--force', action='store_true', help='Reindex url in error')
        parser.add_argument('--worker', nargs=1, type=int, default=[None], help='Worker count (defaults to the available cpu count * 2)')
        parser.add_argument('urls', nargs='*', type=str)

    @staticmethod
    def process(crawl_id, worker_no, options):
        connection.close()
        connection.connect()

        if worker_no == 0:
            last = CrawlerStats.objects.filter(freq=CrawlerStats.MINUTELY).order_by('t').last()
            if last:
                next_stat = last.t
            else:
                next_stat = now()
            next_stat += timedelta(minutes=1)
            prev_stat = None

            next_daily = now() + timedelta(hours=24)
            CrawlerStats.create_daily()

        sleep_count = 0
        while True:
            if worker_no == 0:
                t = now()
                if next_stat < t:
                    prev_stat = CrawlerStats.create(t, prev_stat)
                    next_stat = t + timedelta(minutes=1)
                if next_daily < t:
                    CrawlerStats.create_daily()

            if UrlQueue.crawl(worker_no, crawl_id):
                sleep_count = 0
            else:
                if options['once'] and UrlQueue.objects.filter(error='').count() == 0:
                    break
                if sleep_count == 0:
                    print('%s Idle...' % worker_no)
                sleep_count += 1
                if sleep_count == 60:
                    sleep_count = 0
                sleep(1)

    def handle(self, *args, **options):
        UrlQueue.objects.update(worker_no=None)

        for url in options['urls']:
            UrlQueue.queue(url=url)
        
        if options['requeue']:
            urls = Document.objects.values_list('url', flat=True)
            self.stdout.write('Queuing %i url...' % len(urls))
            for url in urls:
                UrlQueue.queue(url=url)

        if options['force']:
            UrlQueue.objects.update(error='', error_hash='')

        self.stdout.write('Crawl initializing')
        Browser.init()
        self.stdout.write('Crawl starting')
        crawl_id = uuid.uuid4()

        worker_count = options['worker'][0]
        if worker_count is None:
            worker_count = cpu_count() * 2

        workers = []
        for crawler_no in range(worker_count):
            p = Process(target=self.process, args=(crawl_id, crawler_no, options))
            p.start()
            workers.append(p)

        for worker in workers:
            worker.join()

        self.stdout.write('Crawl finished')
