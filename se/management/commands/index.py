from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...browser import Browser
from ...models import Document, UrlPolicy


class Command(BaseCommand):
    help = 'Crawl web pages'

    def __del__(self):
        Browser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='+', type=str)

    def handle(self, *args, **options):
        Document.objects.update(worker_no=None)
        Browser.init()

        for url in options['urls']:
            n = now()
            doc = Document.pick_or_create(url, 999999)
            url_policy = UrlPolicy.get_from_url(doc.url)
            page = url_policy.url_get(doc.url)

            if page.url == doc.url:
                doc.index(page, url_policy, verbose=True, force=True)
            else:
                pint('Got redirect')
            print('Duration %s' % (now() - n))
