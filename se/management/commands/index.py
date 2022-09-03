from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...browser import Browser
from ...models import Document, DomainSetting, UrlPolicy


class Command(BaseCommand):
    help = 'Crawl web pages'

    def __del__(self):
        Browser.destroy()

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='+', type=str)

    def handle(self, *args, **options):
        UrlPolicy.objects.get_or_create(url_prefix='', defaults={'no_crawl': True}) # mandatory default policy
        Document.objects.update(worker_no=None)
        Browser.init()

        for url in options['urls']:
            n = now()
            doc = Document.pick_or_create(url, 999999)
            url_policy = UrlPolicy.get_from_url(doc.url)
            domain = urlparse(doc.url).netloc
            domain_setting, _ = DomainSetting.objects.get_or_create(url_policy=url_policy,
                                                                    domain=domain,
                                                                    defaults={'browse_mode': url_policy.default_browse_mode})
            page = url_policy.url_get(domain_setting, doc.url)

            if page.url == doc.url:
                doc.index(page, url_policy, verbose=True, force=True)
                doc.save()
            else:
                pint('Got redirect')
            print('Duration %s' % (now() - n))
