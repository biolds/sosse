from django.contrib import admin
from django.utils.html import format_html

from .models import Document, QueueWhitelist, UrlQueue, AuthMethod, AuthField, AuthDynamicField

admin.site.enable_nav_sidebar = False
admin.site.register(QueueWhitelist)

admin.site.register(AuthMethod)
admin.site.register(AuthField)
admin.site.register(AuthDynamicField)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    @staticmethod
    def link(obj):
        return format_html('<a href="{}">Link 🔗</a>', obj.url)

    list_display = ('url', 'link', 'lang_iso_639_1', 'title')
    list_filter = ('lang_iso_639_1',)


class UrlQueueUrlFilter(admin.SimpleListFilter):
    title = 'error'
    parameter_name = 'has_error'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(error='')

        if self.value() == 'no':
            return queryset.filter(error='')


@admin.register(UrlQueue)
class UrlQueueAdmin(admin.ModelAdmin):
    @staticmethod
    @admin.display(boolean=True)
    def status(obj):
        return obj.error == ''

    @staticmethod
    def err(obj):
        err_lines = obj.error.splitlines()
        if err_lines:
            return err_lines[-1]

    list_display = ('url', 'status', 'err')
    list_filter = (UrlQueueUrlFilter,)
