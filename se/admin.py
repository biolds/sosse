from urllib.parse import urlencode

from django import forms
from django.db import models
from django.conf import settings
from django.contrib import admin, messages
from django.urls import path
from django.utils.html import format_html
from django.utils.timezone import now
from django.shortcuts import redirect, reverse
from django.template import defaultfilters, response

from .forms import AddToQueueForm
from .models import AuthField, Document, DomainSetting, CrawlPolicy, SearchEngine
from .utils import human_datetime


class SEAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        # Reverse the order to make authentication appear last
        return reversed(super().get_app_list(request))

admin_site = SEAdminSite(name='admin')
admin_site.enable_nav_sidebar = False


def get_admin():
    global admin_site
    return admin_site


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
            return queryset.filter(crawl_next__isnull=False) | queryset.filter(crawl_last__isnull=True)

        if self.value() == 'no':
            return queryset.filter(crawl_next__isnull=True, crawl_last__isnull=False)


@admin.action(description='Crawl now')
def crawl_now(modeladmin, request, queryset):
    queryset.update(crawl_next=now())


@admin.action(description='Force reindex now')
def reindex_now(modeladmin, request, queryset):
    queryset.update(crawl_next=now(), content_hash=None)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('_url', 'fav', 'title', 'lang', 'status', 'err', '_crawl_last', '_crawl_next', 'crawl_dt')
    list_filter = (DocumentQueueFilter, 'lang_iso_639_1', DocumentErrorFilter,)
    search_fields = ['url__regex', 'title__regex']
    fields = ('url', 'crawl_policy', 'domain', 'cached', 'link', 'title', 'status', 'error', 'crawl_first', 'crawl_last', 'crawl_next', 'crawl_dt',
        'crawl_recurse', 'robotstxt_rejected', 'mimetype', 'lang', 'content')
    readonly_fields = fields
    actions = [crawl_now, reindex_now]

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        return [
            path('queue/', self.admin_site.admin_view(self.add_to_queue), name='queue'),
            path('queue_confirm/', self.admin_site.admin_view(self.add_to_queue_confirm), name='queue_confirm')
        ] + urls

    def add_to_queue(self, request):
        context = dict(
           self.admin_site.each_context(request),
           form=AddToQueueForm(),
            title='Crawl a new URL'
        )
        return response.TemplateResponse(request, 'se/add_to_queue.html', context)

    def add_to_queue_confirm(self, request):
        if request.method != 'POST':
            redirect(reverse('admin:queue'))

        form = AddToQueueForm(request.POST)
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title='Crawl a new URL'
        )
        if not form.is_valid():
            return response.TemplateResponse(request, 'se/add_to_queue.html', context)

        if request.POST.get('action') == 'Confirm':
            doc, created = Document.objects.get_or_create(url=form.cleaned_data['url'])
            if not created:
                doc.crawl_next = now()
            doc.save()
            messages.success(request, 'URL was queued.')
            return redirect(reverse('admin:se_document_changelist'))

        crawl_policy = CrawlPolicy.get_from_url(form.cleaned_data['url'])
        context.update({
            'crawl_policy': crawl_policy,
            'url': form.cleaned_data['url'],
            'CrawlPolicy': CrawlPolicy,
            'DomainSetting': DomainSetting,
        })
        if crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_CONSTANT:
            context['recrawl_every'] = human_datetime(crawl_policy.recrawl_dt_min)
        elif crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_ADAPTIVE:
            context.update({
                'recrawl_min': human_datetime(crawl_policy.recrawl_dt_min),
                'recrawl_max': human_datetime(crawl_policy.recrawl_dt_max)
            })
        return response.TemplateResponse(request, 'se/add_to_queue.html', context)

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
        return format_html('<a href="{}">Source page 🔗</a>', obj.url)

    @staticmethod
    def cached(obj):
        return format_html('<a href="{}">Cached version 🔗</a>', obj.get_absolute_url())

    @staticmethod
    def domain(obj):
        crawl_policy = CrawlPolicy.get_from_url(obj.url)
        dom = DomainSetting.get_from_url(obj.url, crawl_policy.default_browse_mode)
        return format_html('<a href="{}">{}</a>', reverse('admin:se_domainsetting_change', args=(dom.id,)), dom)

    @staticmethod
    def lang(obj):
        lang = obj.lang_iso_639_1
        flag = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang, {}).get('flag')

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

    @staticmethod
    def crawl_policy(obj):
        policy = CrawlPolicy.get_from_url(obj.url)
        return format_html('<a href="{}">{}</a>', reverse('admin:se_crawlpolicy_change', args=(policy.id,)), policy)

    @staticmethod
    def _url(obj):
        return format_html('<span title="{}">{}</span>', obj.url, obj.url)


class InlineAuthField(admin.TabularInline):
    model = AuthField


class CrawlPolicyForm(forms.ModelForm):
    class Meta:
        model = CrawlPolicy
        exclude = tuple()

    def clean(self):
        errors = {}
        cleaned_data = super().clean()

        keys_required = {
            'recrawl_dt_min': cleaned_data['recrawl_mode'] in (CrawlPolicy.RECRAWL_ADAPTIVE, CrawlPolicy.RECRAWL_CONSTANT),
            'recrawl_dt_max': cleaned_data['recrawl_mode'] in (CrawlPolicy.RECRAWL_ADAPTIVE,),
        }

        for key, required in keys_required.items():
            if required and cleaned_data.get(key) is None:
                self.add_error(key, 'This field is required when using this recrawl mode')

            if not required and cleaned_data.get(key) is not None:
                self.add_error(key, 'This field must be null when using this recrawl mode')

        if cleaned_data['default_browse_mode'] != DomainSetting.BROWSE_SELENIUM and cleaned_data['take_screenshots']:
            self.add_error('default_browse_mode', 'Browsing mode must be set to Chromium to take screenshots')
            self.add_error('take_screenshots', 'Browsing mode must be set to Chromium to take screenshots')
        return cleaned_data


@admin.register(CrawlPolicy)
class CrawlPolicyAdmin(admin.ModelAdmin):
    inlines = [InlineAuthField]
    form = CrawlPolicyForm
    list_display = ('url_regex', 'condition', 'crawl_depth', 'default_browse_mode', 'recrawl_mode')
    search_fields = ('url_regex',)
    readonly_fields = ('documents', 'auth_cookies',)
    fieldsets = (
        (None, {
            'fields': ('url_regex', 'documents', 'condition', 'mimetype_regex', 'crawl_depth', 'keep_params')
        }),
        ('Browser', {
            'fields': ('default_browse_mode', 'take_screenshots', 'store_extern_links')
        }),
        ('Updates', {
            'fields': ('recrawl_mode', 'recrawl_dt_min', 'recrawl_dt_max', 'hash_mode')
        }),
        ('Authentication', {
            'fields': ('auth_login_url_re', 'auth_form_selector', 'auth_cookies'),
        }),
    )

    @staticmethod
    def documents(obj):
        params = urlencode({'q': obj.url_regex})
        return format_html('<a href="{}">Matching documents</a>', reverse('admin:se_document_changelist') + '?' + params)


@admin.register(DomainSetting)
class DomainSettingAdmin(admin.ModelAdmin):
    list_display = ('domain', 'ignore_robots', 'robots_status', 'browse_mode')
    search_fields = ('domain',)
    fields = ('domain', 'browse_mode', 'ignore_robots', 'robots_status', 'robots_allow', 'robots_disallow')
    readonly_fields = ('domain', 'robots_status', 'robots_allow', 'robots_disallow')
