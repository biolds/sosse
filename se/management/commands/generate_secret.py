from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = 'Generate a secret key to set in the configuration'

    def handle(self, *args, **options):
        # Escape % to avoid value interpolation in the conf file
        # (https://docs.python.org/3/library/configparser.html#interpolation-of-values)
        print(get_random_secret_key().replace('%', '%%'))
