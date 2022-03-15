from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.template import defaultfilters

from .models import Document, DomainPolicy, QueueWhitelist, AuthField, SearchEngine, FavIcon

admin.site.enable_nav_sidebar = False
admin.site.register(QueueWhitelist)


@admin.register(FavIcon)
class FavIconAdmin(admin.ModelAdmin):
    list_display = ('_url', 'fav')

    @staticmethod
    def _url(obj):
        if len(obj.url) > 128:
            return obj.url[:128] + '...'
        return obj.url

    @staticmethod
    def fav(obj):
        if not obj.missing:
            return format_html('<img src="{}" style="widgth: 16px; height: 16px">', reverse('favicon', args=(obj.id,)))


@admin.register(SearchEngine)
class SearchEngineAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'shortcut')


class DocumentErrorFilter(admin.SimpleListFilter):
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


class DocumentQueueFilter(admin.SimpleListFilter):
    title = 'queued'
    parameter_name = 'is_queued'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(crawl_next__isnull=False)

        if self.value() == 'no':
            return queryset.filter(crawl_next__isnull=True)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('url', 'fav', 'link', 'title', 'lang', 'status', 'err', '_crawl_last', '_crawl_next')
    list_filter = (DocumentQueueFilter, 'lang_iso_639_1', DocumentErrorFilter,)
    search_fields = ['url', 'title']

    @staticmethod
    @admin.display(ordering='crawl_next')
    def _crawl_next(obj):
        if obj:
            return defaultfilters.date(obj.crawl_next, 'DATETIME_FORMAT')

    @staticmethod
    @admin.display(ordering='crawl_last')
    def _crawl_last(obj):
        if obj:
            return defaultfilters.date(obj.crawl_last, 'DATETIME_FORMAT')

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

    @staticmethod
    @admin.display(boolean=True)
    def status(obj):
        return obj.error == ''

    @staticmethod
    def err(obj):
        err_lines = obj.error.splitlines()
        if err_lines:
            return err_lines[-1]


class InlineAuthField(admin.TabularInline):
    model = AuthField


@admin.register(DomainPolicy)
class DomainPolicyAdmin(admin.ModelAdmin):
    inlines = [InlineAuthField]
