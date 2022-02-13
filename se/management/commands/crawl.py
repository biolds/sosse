import uuid
from time import sleep

from django.core.management.base import BaseCommand, CommandError
from ...models import UrlQueue, Document


class Command(BaseCommand):
    help = 'Crawl web pages'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Exit when url queue is empty')
        parser.add_argument('--requeue', action='store_true', help='Exit when url queue is empty')
        parser.add_argument('--force', action='store_true', help='Reindex url in error')
        parser.add_argument('urls', nargs='*', type=str)


    def handle(self, *args, **options):
        for url in options['urls']:
            UrlQueue.queue(url=url)
        
        if options['requeue']:
            urls = Document.objects.values_list('url', flat=True)
            self.stdout.write('Queuing %i url...' % len(urls))
            for url in urls:
                UrlQueue.queue(url=url)

        if options['force']:
            UrlQueue.objects.update(error='', error_hash='')

        self.stdout.write('Crawler starting')
        sleep_count = 0
        crawl_id = uuid.uuid4()

        while True:
            if UrlQueue.crawl(crawl_id):
                sleep_count = 0
            else:
                if options['once']:
                    break
                if sleep_count == 0:
                    self.stdout.write('Idle...')
                sleep_count += 1
                if sleep_count == 60:
                    sleep_count = 0
                sleep(1)
        self.stdout.write('Crawler exiting')
