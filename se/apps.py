from django.apps import AppConfig
from django.conf import settings


class SeConfig(AppConfig):
    name = 'se'

    def ready(self):
        from .models import DomainPolicy

        supported_mode = [a[0] for a in DomainPolicy.MODE]
        if settings.BROWSING_METHOD not in supported_mode:
            raise Exception('Unsupported BROWSING_METHOD value %s' % settings.BROWSING_METHOD)
