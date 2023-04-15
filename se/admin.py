# Copyright 2022-2023 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.timezone import now
from django.shortcuts import redirect, reverse
from django.template import defaultfilters, response

from .forms import AddToQueueForm
from .models import AuthField, Document, DomainSetting, CrawlPolicy, SearchEngine, Cookie, ExcludedUrl, WorkerStats
from .utils import human_datetime, human_dt


class SEAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        MODELS_ORDER = (
            ('se', ('CrawlPolicy', 'Document', 'DomainSetting', 'Cookie', 'ExcludedUrl', 'SearchEngine')),
            ('auth', ('Group', 'User'))
        )
        _apps_list = super().get_app_list(request)
        app_list = []

        for app, models in MODELS_ORDER:
            for dj_app in _apps_list:
                if dj_app['app_label'] == app:
                    app_list.append(dj_app)
                    dj_models = dj_app['models']
                    dj_app['models'] = []
                    for model in models:
                        for dj_model in dj_models:
                            if dj_model['object_name'] == model:
                                dj_app['models'].append(dj_model)
                                break
                        else:
                            # The model may not be available due to permission reasons
                            if request.user.is_superuser:
                                raise Exception('object_name not found %s' % model)
        return app_list


admin_site = SEAdminSite(name='admin')
admin_site.enable_nav_sidebar = False


def get_admin():
    global admin_site
    return admin_site


@admin.register(SearchEngine)
class SearchEngineAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'shortcut')
    search_fields = ('short_name', 'shortcut')


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
            queue = Document.objects.filter(crawl_last__isnull=True).order_by('id')
            queue = queue | Document.objects.filter(crawl_last__isnull=False, crawl_next__isnull=False).order_by('crawl_next')
            return queue

        if self.value() == 'no':
            return queryset.filter(crawl_next__isnull=True, crawl_last__isnull=False)


@admin.action(description='Crawl now', permissions=['change'])
def crawl_now(modeladmin, request, queryset):
    queryset.update(crawl_next=now(), content_hash=None)
    return redirect(reverse('admin:crawl_status'))


@admin.action(description='Remove from crawl queue', permissions=['change'])
def remove_from_crawl_queue(modeladmin, request, queryset):
    queryset.update(crawl_next=None)


@admin.action(description='Convert screens to jpeg', permissions=['change'])
def convert_to_jpg(modeladmin, request, queryset):
    for doc in queryset.all():
        if doc.screenshot_format == Document.SCREENSHOT_JPG or not doc.screenshot_file:
            continue
        doc.convert_to_jpg()
        doc.screenshot_format = Document.SCREENSHOT_JPG
        doc.save()


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('_url', 'fav', 'title', 'lang', 'status', 'err', '_crawl_last', '_crawl_next', 'crawl_dt')
    list_filter = (DocumentQueueFilter, 'lang_iso_639_1', DocumentErrorFilter,)
    search_fields = ['url__regex', 'title__regex']
    fields = ('url', 'crawl_policy', 'domain', 'cookies', 'cached', 'link', 'title', 'status',
              'error', 'crawl_first', 'crawl_last', 'crawl_next', 'crawl_dt', 'crawl_recurse',
              'robotstxt_rejected', 'too_many_redirects', 'mimetype', 'lang', '_content')
    readonly_fields = fields
    ordering = ('-crawl_last',)
    actions = [crawl_now, remove_from_crawl_queue, convert_to_jpg]
    list_per_page = settings.SOSSE_ADMIN_PAGE_SIZE

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        return [
            path('<path:object_id>/do_action/', self.admin_site.admin_view(self.do_action), name='doaction'),
            path('queue/', self.admin_site.admin_view(self.add_to_queue), name='queue'),
            path('queue_confirm/', self.admin_site.admin_view(self.add_to_queue_confirm), name='queue_confirm'),
            path('crawl_status/', self.admin_site.admin_view(self.crawl_status), name='crawl_status'),
            path('crawl_status_content/', self.admin_site.admin_view(self.crawl_status_content), name='crawl_status_content'),
        ] + urls

    def do_action(self, request, object_id):
        if not request.user.has_perm('se.change_document'):
            raise PermissionDenied

        action_name = request.POST.get('action')

        for action in self.actions:
            if action.__name__ == action_name:
                break
        else:
            raise Exception('Action %s not support' % action)

        queryset = self.get_queryset(request).filter(id=object_id)
        r = action(self, request, queryset)
        messages.success(request, 'Done.')
        if isinstance(r, HttpResponse):
            return r
        return redirect(reverse('admin:se_document_change', args=(object_id,)))

    def render_change_form(self, request, context, *args, **kwargs):
        context['actions'] = self.get_action_choices(request)
        return super().render_change_form(request, context, *args, **kwargs)

    def add_to_queue(self, request):
        if not request.user.has_perm('se.add_document'):
            raise PermissionDenied
        context = dict(
            self.admin_site.each_context(request),
            form=AddToQueueForm(),
            title='Crawl a new URL'
        )
        return response.TemplateResponse(request, 'admin/add_to_queue.html', context)

    def add_to_queue_confirm(self, request):
        if not request.user.has_perm('se.add_document'):
            raise PermissionDenied
        if request.method != 'POST':
            redirect(reverse('admin:queue'))

        form = AddToQueueForm(request.POST)
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title='Crawl a new URL'
        )
        if not form.is_valid():
            return response.TemplateResponse(request, 'admin/add_to_queue.html', context)

        if request.POST.get('action') == 'Confirm':
            crawl_recurse = form.cleaned_data.get('crawl_depth') or 0
            doc, created = Document.objects.get_or_create(url=form.cleaned_data['url'], defaults={'crawl_recurse': crawl_recurse})
            if not created:
                doc.crawl_next = now()
                if crawl_recurse:
                    doc.crawl_recurse = crawl_recurse

            doc.save()
            messages.success(request, 'URL was queued.')
            return redirect(reverse('admin:crawl_status'))

        crawl_policy = CrawlPolicy.get_from_url(form.cleaned_data['url'])
        form = AddToQueueForm(request.POST, initial={'crawl_depth': crawl_policy.crawl_depth})
        form.is_valid()
        context.update({
            'crawl_policy': crawl_policy,
            'url': form.cleaned_data['url'],
            'CrawlPolicy': CrawlPolicy,
            'DomainSetting': DomainSetting,
            'form': form
        })
        if crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_CONSTANT:
            context['recrawl_every'] = human_datetime(crawl_policy.recrawl_dt_min)
        elif crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_ADAPTIVE:
            context.update({
                'recrawl_min': human_datetime(crawl_policy.recrawl_dt_min),
                'recrawl_max': human_datetime(crawl_policy.recrawl_dt_max)
            })
        return response.TemplateResponse(request, 'admin/add_to_queue.html', context)

    def _crawl_status_context(self, request):
        _now = now()
        context = dict(
            self.admin_site.each_context(request),
            title='Crawl status',
            now=_now
        )

        queue_new_count = Document.objects.filter(crawl_last__isnull=True).count()
        queue_sched_count = Document.objects.filter(crawl_last__isnull=False,
                                                    crawl_next__isnull=False).count()

        QUEUE_SIZE = 7
        queue = list(Document.objects.filter(crawl_last__isnull=True).order_by('id')[:QUEUE_SIZE])
        if len(queue) < QUEUE_SIZE:
            queue = queue + list(Document.objects.filter(crawl_last__isnull=False,
                                                         crawl_next__isnull=False).order_by('crawl_next', 'id')[:QUEUE_SIZE - len(queue)])
            for doc in queue:
                doc.pending = True

        queue.reverse()

        history = list(Document.objects.filter(crawl_last__isnull=False).order_by('-crawl_last')[:QUEUE_SIZE])

        for doc in queue:
            if doc in history:
                history.remove(doc)

        queue = queue + history

        for doc in queue:
            if doc.crawl_next:
                doc.crawl_next_human = human_dt(doc.crawl_next, True)
            if doc.crawl_last:
                doc.crawl_last_human = human_dt(doc.crawl_last, True)

        context.update({
            'crawlers': WorkerStats.live_state(),
            'pause': WorkerStats.objects.filter(state='paused').count() == 0,
            'queue': queue,
            'settings': settings,
            'queue_new_count': queue_new_count,
            'queue_sched_count': queue_sched_count,
        })
        return context

    def crawl_status(self, request):
        if not request.user.has_perm('se.view_crawlerstats'):
            raise PermissionDenied
        if request.method == 'POST':
            if not request.user.has_perm('se.change_crawlerstats'):
                raise PermissionDenied
            if 'pause' in request.POST:
                WorkerStats.objects.update(state='paused')
            if 'resume' in request.POST:
                WorkerStats.objects.update(state='running')
        context = self._crawl_status_context(request)
        return response.TemplateResponse(request, 'admin/crawl_status.html', context)

    def crawl_status_content(self, request):
        if not request.user.has_perm('se.view_crawlerstats'):
            raise PermissionDenied
        context = self._crawl_status_context(request)
        return response.TemplateResponse(request, 'admin/crawl_status_content.html', context)

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
    def cookies(obj):
        return format_html('<a href="{}">Cookies</a>', reverse('admin:se_cookie_changelist') + '?q=' + obj.url)

    @staticmethod
    def lang(obj):
        return obj.lang_flag()

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
    @admin.display(ordering='url')
    def _url(obj):
        return format_html('<span title="{}">{}</span>', obj.url, obj.url)

    @staticmethod
    def _content(obj):
        if obj.redirect_url:
            return 'Redirected to %s' % obj.redirect_url
        return obj.content

    def delete_model(self, request, obj):
        obj.delete_screenshot()
        return super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset.all():
            obj.delete_screenshot()
        return super().delete_queryset(request, queryset)


class InlineAuthField(admin.TabularInline):
    model = AuthField


class CrawlPolicyForm(forms.ModelForm):
    class Meta:
        model = CrawlPolicy
        exclude = tuple()

    def clean(self):
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

        if cleaned_data['default_browse_mode'] != DomainSetting.BROWSE_SELENIUM:
            if cleaned_data['take_screenshots']:
                self.add_error('default_browse_mode', 'Browsing mode must be set to Chromium to take screenshots')
                self.add_error('take_screenshots', 'Browsing mode must be set to Chromium to take screenshots')
            elif cleaned_data['script']:
                self.add_error('default_browse_mode', 'Browsing mode must be set to Chromium to run a script')
                self.add_error('script', 'Browsing mode must be set to Chromium to run a script')
        return cleaned_data


@admin.register(CrawlPolicy)
class CrawlPolicyAdmin(admin.ModelAdmin):
    inlines = [InlineAuthField]
    form = CrawlPolicyForm
    list_display = ('url_regex', 'docs', 'condition', 'crawl_depth', 'default_browse_mode', 'recrawl_mode')
    search_fields = ('url_regex',)
    readonly_fields = ('documents',)
    fieldsets = (
        (None, {
            'fields': ('url_regex', 'documents', 'condition', 'mimetype_regex', 'crawl_depth', 'keep_params')
        }),
        ('Browser', {
            'fields': ('default_browse_mode', 'take_screenshots', 'screenshot_format', 'script', 'store_extern_links')
        }),
        ('Updates', {
            'fields': ('recrawl_mode', 'recrawl_dt_min', 'recrawl_dt_max', 'hash_mode')
        }),
        ('Authentication', {
            'fields': ('auth_login_url_re', 'auth_form_selector'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.url_regex == '.*':
            return self.readonly_fields + ('url_regex',)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        if obj and obj.url_regex == '.*':
            return False
        return super().has_delete_permission(request, obj)

    @staticmethod
    def documents(obj):
        params = urlencode({'q': obj.url_regex})
        return format_html('<a href="{}">Matching documents</a>', reverse('admin:se_document_changelist') + '?' + params)

    @staticmethod
    def docs(obj):
        count = Document.objects.filter(url__regex=obj.url_regex).count()
        params = urlencode({'q': obj.url_regex})
        return format_html('<a href="{}">{}</a>', reverse('admin:se_document_changelist') + '?' + params, count)


@admin.register(DomainSetting)
class DomainSettingAdmin(admin.ModelAdmin):
    list_display = ('domain', 'ignore_robots', 'robots_status', 'browse_mode')
    search_fields = ('domain',)
    fields = ('domain', 'documents', 'browse_mode', 'ignore_robots', 'robots_status', 'robots_allow', 'robots_disallow')
    readonly_fields = ('domain', 'documents', 'robots_status', 'robots_allow', 'robots_disallow')

    @staticmethod
    def documents(obj):
        params = urlencode({'q': '^https?://%s/' % obj.domain})
        return format_html('<a href="{}">Matching documents</a>', reverse('admin:se_document_changelist') + '?' + params)


@admin.register(Cookie)
class CookieAdmin(admin.ModelAdmin):
    list_display = ('domain', 'domain_cc', 'path', 'name', 'value', 'expires')
    search_fields = ('domain', 'path')
    ordering = ('domain', 'domain_cc', 'path', 'name')
    exclude = tuple()

    def get_search_results(self, request, queryset, search_term):
        if search_term.startswith('http://') or search_term.startswith('https://'):
            cookies = Cookie.get_from_url(search_term, queryset, expire=False)
            cookies = sorted(cookies, key=lambda x: x.name)
            _cookies = Cookie.objects.filter(id__in=[c.id for c in cookies])
            return _cookies, False
        return super().get_search_results(request, queryset, search_term)


@admin.register(ExcludedUrl)
class ExcludedUrlAdmin(admin.ModelAdmin):
    list_display = ('url',)
    search_fields = ('url', 'domment')
    ordering = ('url',)
