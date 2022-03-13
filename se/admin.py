from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Document, DomainPolicy, QueueWhitelist, UrlQueue, AuthMethod, AuthField, SearchEngine

admin.site.enable_nav_sidebar = False
admin.site.register(QueueWhitelist)
admin.site.register(DomainPolicy)


@admin.register(SearchEngine)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'shortcut')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    @staticmethod
    def fav(obj):
        if obj.favicon and not obj.favicon.missing:
            return format_html('<img src="{}" style="widgth: 16px; height: 16px">', reverse('favicon', args=(obj.favicon.id,)))

    @staticmethod
    def link(obj):
        return format_html('<a href="{}">Link 🔗</a>', obj.url)

    @staticmethod
    def lang(obj):
        lang = obj.lang_iso_639_1
        flag = settings.MYSE_LANGDETECT_TO_POSTGRES.get(lang, {}).get('flag')

        if flag:
            lang = f'{flag} {lang}'

        return lang

    list_display = ('url', 'fav', 'link', 'title', 'lang')
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


class InlineAuthField(admin.TabularInline):
    model = AuthField


@admin.register(AuthMethod)
class AuthMethodAdmin(admin.ModelAdmin):
    inlines = [InlineAuthField]
