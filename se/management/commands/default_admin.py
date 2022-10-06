import sys

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Outputs default configuration file to stdout'

    def handle(self, *args, **options):
        if User.objects.count() != 0:
            self.stdout.write('The database already has a user, skipping defualt user creation')
            sys.exit(0)

        user = User.objects.create(username='admin', is_superuser=True, is_staff=True, is_active=True)
        user.set_password('admin')
        user.save()
        self.stdout.write('Default user "admin", with password "admin" was created')
