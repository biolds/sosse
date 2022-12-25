from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test


def login_required(func):
    from django.conf import settings
    if settings.SOSSE_ANONYMOUS_SEARCH:
        return func
    else:
        decorator = user_passes_test(
            lambda u: u.is_authenticated,
            login_url=None,
            redirect_field_name=REDIRECT_FIELD_NAME
        )
        return decorator(func)
