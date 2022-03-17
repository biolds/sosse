from django.apps import AppConfig
from django.conf import settings


class SeConfig(AppConfig):
    name = 'se'

    def ready(self):
        from .models import DomainPolicy

        supported_mode = [a[0] for a in DomainPolicy.MODE]
        if settings.BROWSING_MODE not in supported_mode:
            raise Exception('Unsupported BROWSING_MODE value %s' % settings.BROWSING_MODE)

        supported_mode = [a[0] for a in DomainPolicy.RECRAWL_MODE]
        if settings.DEFAULT_RECRAWL_MODE not in supported_mode:
            raise Exception('Unsupported DEFAULT_RECRAWL_MODE value %s' % settings.DEFAULT_RECRAWL_MODE)

        if settings.HASH_MODE not in ('raw', 'clear_numbers'):
            raise Exception('Unsupported HASH_MODE value %s' % settings.DEFAULT_RECRAWL_MODE)
