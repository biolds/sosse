# Copyright Travis Jensen
# Copied from https://stackoverflow.com/questions/4088253/django-how-to-detect-test-environment-check-determine-if-tests-are-being-ru/7651002#7651002
from django.conf import settings
from django.test.runner import DiscoverRunner


class SuiteRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings.TEST_MODE = True
