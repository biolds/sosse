from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class SEConfig(AppConfig):
    name = 'se'
    verbose_name = 'Search Engine'
    default_auto_field = 'django.db.models.AutoField'


class SEAdminConfig(AdminConfig):
    default_site = 'se.admin.get_admin'
