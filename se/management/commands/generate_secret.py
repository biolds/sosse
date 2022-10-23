from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key

from sosse.conf import Conf


class Command(BaseCommand):
    help = 'Generate a secret key to set in the configuration'

    def handle(self, *args, **options):
        print(get_random_secret_key())
