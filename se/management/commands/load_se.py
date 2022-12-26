from django.core.management.base import BaseCommand


from ...models import SearchEngine


class Command(BaseCommand):
    help = 'Load a search engine definition from an OpenSearch xml file'

    def add_arguments(self, parser):
        parser.add_argument('url', nargs=1, type=str)

    def handle(self, *args, **options):
        SearchEngine.parse_xml_file(options['url'][0])
