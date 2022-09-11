from datetime import datetime, timedelta
from multiprocessing import cpu_count, Process
from time import sleep

from django.conf import settings
from django.db import connection
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from ...browser import Browser
from ...models import CrawlerStats, Document, UrlPolicy, WorkerStats, MINUTELY


class Command(BaseCommand):
    help = 'Crawl web pages'

    def __del__(self):
        Browser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='*', type=str)

    @staticmethod
    def process(worker_no, options):
        connection.close()
        connection.connect()

        print('Worker %i initializing' % worker_no)
        Browser.init()
        print('Worker %i starting' % worker_no)

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

            if Document.crawl(worker_no):
                sleep_count = 0
            else:
                if sleep_count == 0:
                    print('%s Idle...' % worker_no)
                sleep_count += 1
                if sleep_count == 60:
                    sleep_count = 0
                sleep(1)

    def handle(self, *args, **options):
        Document.objects.exclude(worker_no=None).update(worker_no=None)
        UrlPolicy.objects.get_or_create(url_regex='.*', defaults={'crawl_when': UrlPolicy.CRAWL_NEVER}) # mandatory default policy

        for url in options['urls']:
            doc = Document.queue(url, None, 0)

        self.stdout.write('Crawl initializing')

        worker_count = settings.OSSE_CRAWLER_COUNT
        if worker_count is None:
            worker_count = cpu_count()

        workers = []
        for crawler_no in range(worker_count):
            p = Process(target=self.process, args=(crawler_no, options))
            p.start()
            workers.append(p)
            sleep(5)

        for worker in workers:
            worker.join()

        self.stdout.write('Crawl finished')
