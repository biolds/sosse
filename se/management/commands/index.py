from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...browser import Browser
from ...models import Document, DomainSetting, CrawlPolicy


class Command(BaseCommand):
    help = 'Crawl web pages'

    def __del__(self):
        Browser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='+', type=str)

    def handle(self, *args, **options):
        CrawlPolicy.objects.get_or_create(url_regex='.*', defaults={'crawl_when': CrawlPolicy.CRAWL_NEVER}) # mandatory default policy
        Document.objects.update(worker_no=None)
        Browser.init()

        for url in options['urls']:
            n = now()
            doc = Document.pick_or_create(url, 999999)
            crawl_policy = CrawlPolicy.get_from_url(doc.url)
            domain = urlparse(doc.url).netloc
            domain_setting, _ = DomainSetting.objects.get_or_create(crawl_policy=crawl_policy,
                                                                    domain=domain,
                                                                    defaults={'browse_mode': crawl_policy.default_browse_mode})
            page = crawl_policy.url_get(domain_setting, doc.url)

            if page.url == doc.url:
                doc.index(page, crawl_policy, verbose=True, force=True)
                doc.save()
            else:
                print('Got redirect')
            print('Duration %s' % (now() - n))
