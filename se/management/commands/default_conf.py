from django.core.management.base import BaseCommand

from sosse.conf import Conf


class Command(BaseCommand):
    help = 'Outputs default configuration file to stdout'

    def handle(self, *args, **options):
        print(Conf.generate_default())
