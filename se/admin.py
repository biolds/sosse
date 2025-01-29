# Copyright 2022-2025 Laurent Defert
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

from copy import copy
from datetime import timedelta
from urllib.parse import quote_plus, urlencode

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect, reverse
from django.template import defaultfilters
from django.template.loader import render_to_string
from django.urls import path
from django.utils.html import format_html
from django.utils.timezone import now

from .add_to_queue import AddToQueueConfirmationView, AddToQueueView
from .analytics import AnalyticsView
from .cookie import Cookie
from .crawl_policy import CrawlPolicy
from .crawl_queue import CrawlQueueContentView, CrawlQueueView
from .crawlers import CrawlersContentView, CrawlersView
from .document import Document
from .domain_setting import DomainSetting
from .html_asset import HTMLAsset
from .models import AuthField, ExcludedUrl, Link, SearchEngine
from .utils import mimetype_icon, reverse_no_escape


class SEAdminSite(admin.AdminSite):
    enable_nav_sidebar = False
    index_title = "Administration"

    def get_app_list(self, request):
        MODELS_ORDER = (
            (
                "se",
                (
                    "CrawlPolicy",
                    "Document",
                    "DomainSetting",
                    "Cookie",
                    "ExcludedUrl",
                    "SearchEngine",
                    "HTMLAsset",
                ),
            ),
            ("auth", ("Group", "User")),
        )
        _apps_list = super().get_app_list(request)
        app_list = []

        for app, _models in MODELS_ORDER:
            for dj_app in _apps_list:
                if dj_app["app_label"] == app:
                    app_list.append(dj_app)
                    dj_models = dj_app["models"]
                    dj_app["models"] = []
                    for model in _models:
                        for dj_model in dj_models:
                            if dj_model["object_name"] == model:
                                dj_app["models"].append(dj_model)
                                break
                        else:
                            # The model may not be available due to permission reasons
                            if request.user.is_superuser and model != "HTMLAsset":
                                raise Exception(f"object_name not found {model}")

                    for dj_model in dj_models:
                        if dj_model["object_name"] not in _models:
                            raise Exception(f"Model {dj_model['object_name']} not referenced in MODELS_ORDER")
        return app_list


admin_site = SEAdminSite(name="admin")


def get_admin():
    global admin_site
    return admin_site


class CharFieldForm(forms.ModelForm):
    """Base form that displays TextField to TextInputs."""

    TEXT_FIELDS = tuple()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in getattr(self, "TEXT_FIELDS"):
                continue
            if isinstance(field.widget, forms.Textarea):
                # Same width as text areas
                widget = forms.TextInput(attrs={"style": "width: 610px"})
                self.fields[name].widget = widget


class ConflictingSearchEngineFilter(admin.SimpleListFilter):
    title = "conflicting"
    parameter_name = "conflict"

    def lookups(self, request, model_admin):
        return (("yes", "Conflicting"),)

    @staticmethod
    def conflicts(queryset):
        return (
            SearchEngine.objects.values("shortcut")
            .annotate(shortcut_count=models.Count("shortcut"))
            .filter(shortcut_count__gt=1)
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            conflicts = self.conflicts(queryset).values_list("shortcut")
            return queryset.filter(shortcut__in=conflicts)

        return queryset


@admin.register(SearchEngine)
class SearchEngineAdmin(admin.ModelAdmin):
    list_display = ("short_name", "shortcut")
    search_fields = ("short_name", "shortcut")
    list_filter = (ConflictingSearchEngineFilter,)


class DocumentErrorFilter(admin.SimpleListFilter):
    title = "error"
    parameter_name = "has_error"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(error="")

        if self.value() == "no":
            return queryset.filter(error="")


class DocumentQueueFilter(admin.SimpleListFilter):
    title = "queued"
    parameter_name = "queued"

    def lookups(self, request, model_admin):
        return (
            ("new", "New"),
            ("pending", "Pending"),
            ("recurring", "Recurring"),
        )

    def queryset(self, request, queryset):
        if self.value() == "new":
            return queryset.filter(crawl_last__isnull=True)
        if self.value() == "pending":
            return queryset.filter(models.Q(crawl_last__isnull=True) | models.Q(crawl_next__lte=now()))

        if self.value() == "recurring":
            return queryset.filter(crawl_last__isnull=False, crawl_next__isnull=False)
        return queryset


class DocumentOrphanFilter(admin.SimpleListFilter):
    title = "orphan"
    parameter_name = "orphan"

    def lookups(self, request, model_admin):
        return (
            ("no_children", "No children"),
            ("no_parent", "No parent"),
            ("full", "No parent or children"),
        )

    def queryset(self, request, queryset):
        links = Link.objects.exclude(doc_from__isnull=True)
        links = links.exclude(doc_to__isnull=True)

        if self.value() in ("no_children", "full"):
            queryset = queryset.filter(redirect_url__isnull=True)
            children = set(links.values_list("doc_from", flat=True).distinct())
            queryset = queryset.exclude(id__in=children)

        if self.value() in ("no_parent", "full"):
            parents = set(links.values_list("doc_to", flat=True).distinct())
            queryset = queryset.exclude(id__in=parents)
            redirects_url = Document.objects.filter(redirect_url__isnull=False).values_list("redirect_url", flat=True)
            queryset = queryset.exclude(url__in=redirects_url)

        return queryset


@admin.action(description="Crawl now", permissions=["change"])
def crawl_now(modeladmin, request, queryset):
    queryset.update(crawl_next=now(), content_hash=None)
    return redirect(reverse("admin:crawl_queue"))


@admin.action(description="Remove from crawl queue", permissions=["change"])
def remove_from_crawl_queue(modeladmin, request, queryset):
    queryset.update(crawl_next=None)


@admin.action(description="Convert screens to jpeg", permissions=["change"])
def convert_to_jpg(modeladmin, request, queryset):
    for doc in queryset.all():
        if doc.screenshot_format == Document.SCREENSHOT_JPG or doc.screenshot_count == 0:
            continue
        doc.convert_to_jpg()
        doc.screenshot_format = Document.SCREENSHOT_JPG
        doc.save()


@admin.action(description="Crawl later", permissions=["change"])
def crawl_later(modeladmin, request, queryset):
    queryset.update(crawl_next=now() + timedelta(days=1))
    return redirect(reverse("admin:crawl_queue"))


@admin.action(description="Switch hidden", permissions=["change"])
def switch_hidden(modeladmin, request, queryset):
    queryset.update(
        hidden=models.Case(
            models.When(hidden=True, then=models.Value(False)),
            models.When(hidden=False, then=models.Value(True)),
        )
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "_url",
        "_title",
        "lang",
        "status",
        "err",
        "_crawl_last",
        "_crawl_next",
        "_modified_date",
        "crawl_dt",
    )
    list_filter = (
        DocumentQueueFilter,
        "lang_iso_639_1",
        DocumentErrorFilter,
        "show_on_homepage",
        "hidden",
        DocumentOrphanFilter,
    )
    search_fields = ["url__regex", "title__regex"]
    ordering = ("-crawl_last",)
    actions = [crawl_now, remove_from_crawl_queue, convert_to_jpg, switch_hidden]
    if settings.DEBUG:
        actions += [crawl_later]
    list_per_page = settings.SOSSE_ADMIN_PAGE_SIZE

    fieldsets = (
        (
            "📖 Main",
            {
                "fields": (
                    "_title",
                    "_links",
                    "show_on_homepage",
                    "hidden",
                    "_status",
                )
            },
        ),
        (
            "📂 Data",
            {
                "fields": (
                    "robotstxt_rejected",
                    "too_many_redirects",
                    "_mimetype",
                    "_lang_txt",
                    "_content",
                )
            },
        ),
        (
            "🕑 Crawl info",
            {
                "fields": (
                    "crawl_first",
                    "modified_date",
                    "_crawl_last_txt",
                    "_crawl_next_txt",
                    "crawl_dt",
                    "crawl_recurse",
                )
            },
        ),
    )
    readonly_fields = [
        "_title",
        "_links",
        "_status",
        "robotstxt_rejected",
        "too_many_redirects",
        "_mimetype",
        "_lang_txt",
        "_content",
        "crawl_first",
        "modified_date",
        "_crawl_last_txt",
        "_crawl_next_txt",
        "crawl_dt",
        "crawl_recurse",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                "<path:object_id>/do_action/",
                self.admin_site.admin_view(self.do_action),
                name="doaction",
            ),
            path("analytics/", self.admin_site.admin_view(self.analytics), name="analytics"),
            path("queue/", self.admin_site.admin_view(self.add_to_queue), name="queue"),
            path(
                "queue_confirm/",
                self.admin_site.admin_view(self.add_to_queue_confirm),
                name="queue_confirm",
            ),
            path(
                "crawlers/",
                self.admin_site.admin_view(self.crawlers),
                name="crawlers",
            ),
            path(
                "crawlers_content/",
                self.admin_site.admin_view(self.crawlers_content),
                name="crawlers_content",
            ),
            path(
                "crawl_queue/",
                self.admin_site.admin_view(self.crawl_queue),
                name="crawl_queue",
            ),
            path(
                "crawl_queue_content/",
                self.admin_site.admin_view(self.crawl_queue_content),
                name="crawl_queue_content",
            ),
        ] + urls

    def do_action(self, request, object_id):
        if not request.user.has_perm("se.change_document"):
            raise PermissionDenied

        action_name = request.POST.get("action")

        for action in self.actions:
            if action.__name__ == action_name:
                break
        else:
            raise Exception(f"Action {action} not support")

        queryset = self.get_queryset(request).filter(id=object_id)
        r = action(self, request, queryset)
        messages.success(request, "Done.")
        if isinstance(r, HttpResponse):
            return r
        return redirect(reverse("admin:se_document_change", args=(object_id,)))

    def get_fields(self, request, obj=None):
        fields = copy(super().get_fields(request, obj))
        if not settings.SOSSE_BROWSABLE_HOME:
            fields.remove("show_on_homepage")
        return fields

    def render_change_form(self, request, context, *args, **kwargs):
        context["actions"] = self.get_action_choices(request)
        return super().render_change_form(request, context, *args, **kwargs)

    def lookup_allowed(self, lookup, value):
        if lookup in ("linked_from__doc_from", "links_to__doc_to"):
            return True
        return super().lookup_allowed(lookup, value)

    def add_to_queue(self, request):
        return AddToQueueView.as_view(admin_site=self.admin_site)(request)

    def add_to_queue_confirm(self, request):
        return AddToQueueConfirmationView.as_view(admin_site=self.admin_site)(request)

    def crawlers(self, request):
        return CrawlersView.as_view(admin_site=self.admin_site)(request)

    def crawlers_content(self, request):
        return CrawlersContentView.as_view(admin_site=self.admin_site)(request)

    def crawl_queue(self, request):
        return CrawlQueueView.as_view(admin_site=self.admin_site)(request)

    def crawl_queue_content(self, request):
        return CrawlQueueContentView.as_view(admin_site=self.admin_site)(request)

    def analytics(self, request):
        return AnalyticsView.as_view()(request)

    @staticmethod
    @admin.display(ordering="crawl_next")
    def _crawl_next(obj):
        if obj:
            return defaultfilters.date(obj.crawl_next, "DATETIME_FORMAT")

    @staticmethod
    @admin.display(description="Crawl next")
    def _crawl_next_txt(obj):
        if obj:
            if obj.crawl_next:
                return defaultfilters.date(obj.crawl_next, "DATETIME_FORMAT")
            elif obj.crawl_last:
                return "No crawl scheduled"
            elif not obj.crawl_last:
                return "When a worker is available"

    @staticmethod
    @admin.display(ordering="crawl_last")
    def _crawl_last(obj):
        if obj:
            return defaultfilters.date(obj.crawl_last, "DATETIME_FORMAT")

    @staticmethod
    @admin.display(description="Crawl last")
    def _crawl_last_txt(obj):
        if obj:
            if obj.crawl_last:
                return defaultfilters.date(obj.crawl_last, "DATETIME_FORMAT")
            else:
                return "Not yet crawled"

    @staticmethod
    @admin.display(ordering="modified_date")
    def _modified_date(obj):
        if obj:
            return defaultfilters.date(obj.modified_date, "DATETIME_FORMAT")

    @staticmethod
    def lang(obj):
        return obj.lang_flag()

    @staticmethod
    @admin.display(boolean=True)
    def status(obj):
        return obj.error == ""

    @staticmethod
    def err(obj):
        err_lines = obj.error.splitlines()
        if err_lines:
            return err_lines[-1]

    @staticmethod
    @admin.display(ordering="url")
    def _url(obj):
        return format_html('<span title="{}">{}</span>', obj.url, obj.url)

    @staticmethod
    @admin.display(ordering="title", description="Title")
    def _title(obj):
        fav = ""
        if obj.favicon and not obj.favicon.missing:
            fav = format_html(
                '<img src="{}" style="widgth: 16px; height: 16px">',
                reverse("favicon", args=(obj.favicon.id,)),
            )

        title = obj.get_title_label()
        return format_html('<span title="{}">{} {}</span>', title, fav, title)

    @staticmethod
    @admin.display(description="Links")
    def _links(obj):
        try:
            crawl_policy = CrawlPolicy.get_from_url(obj.url)
            policy = format_html(
                '⚡&nbsp<a href="{}">Crawl&nbspPolicy&nbsp{}</a>',
                reverse("admin:se_crawlpolicy_change", args=(crawl_policy.id,)),
                crawl_policy,
            )

            domain_setting = DomainSetting.get_from_url(obj.url, crawl_policy.default_browse_mode)
            domain = format_html(
                '🕸&nbsp<a href="{}">Domain</a>',
                reverse("admin:se_domainsetting_change", args=(domain_setting.id,)),
            )

            cookies = format_html(
                '🍪&nbsp<a href="{}">Cookies</a>',
                reverse("admin:se_cookie_changelist") + "?q=" + quote_plus(obj.url),
            )

            source = obj.get_source_link()
            archive = format_html('🔖&nbsp<a href="{}">Archive</a>', obj.get_absolute_url())

            links_to_here_url = reverse("admin:se_document_changelist") + f"?links_to__doc_to={obj.id}"
            links_to_here = format_html('🔗&nbsp<a href="{}">Links to here</a>', links_to_here_url)

            links_from_here_url = reverse("admin:se_document_changelist") + f"?linked_from__doc_from={obj.id}"
            links_from_here = format_html('🔗&nbsp<a href="{}">Links from here</a>', links_from_here_url)

            return format_html(
                '<span>{}</span><span class="label_tag">{}</span><span class="label_tag">{}</span><span class="label_tag">{}</span>'
                '<span class="label_tag">{}</span><span class="label_tag">{}</span><span class="label_tag">{}</span>',
                policy,
                domain,
                cookies,
                archive,
                links_to_here,
                links_from_here,
                source,
            )
        except Exception as e:
            return format_html("Error: {}", e)

    @staticmethod
    @admin.display(description="Status")
    def _status(obj):
        status = obj.error == ""
        icon = "icon-yes.svg" if status else "icon-no.svg"
        return format_html(
            '<pre style="margin-top: 0; overflow-x: auto"><img src="{}" alt="{}" /> {}</pre>',
            f"{settings.STATIC_URL}admin/img/{icon}",
            str(status),
            obj.error,
        )

    @staticmethod
    @admin.display(description="Mimetype")
    def _mimetype(obj):
        icon = mimetype_icon(obj.mimetype)
        return f"{icon} {obj.mimetype}"

    @staticmethod
    @admin.display(description="Language")
    def _lang_txt(obj):
        if obj.lang_iso_639_1:
            return obj.lang_flag(full=True)

    @staticmethod
    @admin.display(description="Content")
    def _content(obj):
        if obj.redirect_url:
            url = reverse_no_escape("archive", args=[obj.redirect_url])
            return format_html('This page redirects to <a href="{}">{}</a>', url, obj.redirect_url)
        return obj.content

    def delete_model(self, request, obj):
        obj.delete_all()
        return super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset.all():
            obj.delete_all()
        return super().delete_queryset(request, queryset)


class InlineAuthField(admin.TabularInline):
    model = AuthField


class CrawlPolicyForm(CharFieldForm):
    TEXT_FIELDS = ("url_regex", "script")

    class Meta:
        model = CrawlPolicy
        exclude = tuple()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance and instance.url_regex == "(default)":
            self._meta.help_texts = {"url_regex": None}

    def clean(self):
        cleaned_data = super().clean()

        keys_required = {
            "recrawl_dt_min": cleaned_data["recrawl_mode"]
            in (CrawlPolicy.RECRAWL_ADAPTIVE, CrawlPolicy.RECRAWL_CONSTANT),
            "recrawl_dt_max": cleaned_data["recrawl_mode"] in (CrawlPolicy.RECRAWL_ADAPTIVE,),
        }

        for key, required in keys_required.items():
            if required and cleaned_data.get(key) is None:
                self.add_error(key, "This field is required when using this recrawl mode")

            if not required and cleaned_data.get(key) is not None:
                self.add_error(key, "This field must be null when using this recrawl mode")

        if cleaned_data["default_browse_mode"] not in (
            DomainSetting.BROWSE_CHROMIUM,
            DomainSetting.BROWSE_FIREFOX,
        ):
            if cleaned_data["thumbnail_mode"] in (
                CrawlPolicy.THUMBNAIL_MODE_SCREENSHOT,
                CrawlPolicy.THUMBNAIL_MODE_PREV_OR_SCREEN,
            ):
                self.add_error(
                    "default_browse_mode",
                    "Browsing mode must be set to Chromium or Firefox to take screenshot as thumbnails",
                )
                self.add_error(
                    "thumbnail_mode",
                    "Browsing mode must be set to Chromium or Firefox to take screenshot as thumbnails",
                )
            if cleaned_data["take_screenshots"]:
                self.add_error(
                    "default_browse_mode",
                    "Browsing mode must be set to Chromium or Firefox to take screenshots",
                )
                self.add_error(
                    "take_screenshots",
                    "Browsing mode must be set to Chromium or Firefox to take screenshots",
                )
            if cleaned_data["script"]:
                self.add_error(
                    "default_browse_mode",
                    "Browsing mode must be set to Chromium or Firefox to run a script",
                )
                self.add_error(
                    "script",
                    "Browsing mode must be set to Chromium or Firefox to run a script",
                )
        return cleaned_data


@admin.action(description="Enable/disable", permissions=["change"])
def crawl_policy_enable_disable(modeladmin, request, queryset):
    queryset.exclude(url_regex="(default)").update(
        enabled=models.Case(
            models.When(enabled=True, then=models.Value(False)),
            models.When(enabled=False, then=models.Value(True)),
        )
    )


@admin.action(description="Copy", permissions=["change"])
def crawl_policy_switch(modeladmin, request, queryset):
    for crawl_policy in queryset.all():
        crawl_policy.id = None
        crawl_policy.url_regex = f"Copy of {crawl_policy.url_regex}"
        crawl_policy.save()


@admin.register(CrawlPolicy)
class CrawlPolicyAdmin(admin.ModelAdmin):
    inlines = [InlineAuthField]
    form = CrawlPolicyForm
    list_display = (
        "url_regex",
        "enabled",
        "docs",
        "crawl_policy_desc",
    )
    list_filter = ("enabled",)
    search_fields = ("url_regex",)
    readonly_fields = ("documents",)
    fieldsets = (
        (
            "⚡ Crawl",
            {
                "fields": (
                    "url_regex",
                    "enabled",
                    "documents",
                    "recursion",
                    "recursion_depth",
                    "mimetype_regex",
                    "keep_params",
                    "store_extern_links",
                    "hide_documents",
                    "remove_nav_elements",
                    "thumbnail_mode",
                )
            },
        ),
        (
            "🌍  Browser",
            {
                "fields": (
                    "default_browse_mode",
                    "take_screenshots",
                    "screenshot_format",
                    "script",
                )
            },
        ),
        (
            "🔖 Archive",
            {
                "fields": (
                    "snapshot_html",
                    "snapshot_exclude_url_re",
                    "snapshot_exclude_mime_re",
                    "snapshot_exclude_element_re",
                )
            },
        ),
        (
            "🕑 Recurrence",
            {
                "fields": (
                    "recrawl_mode",
                    "recrawl_dt_min",
                    "recrawl_dt_max",
                    "hash_mode",
                )
            },
        ),
        (
            "🔒 Authentication",
            {
                "fields": ("auth_login_url_re", "auth_form_selector"),
            },
        ),
    )
    actions = [crawl_policy_enable_disable, crawl_policy_switch]

    def get_queryset(self, request):
        # Keep the (default) policy at the top
        return CrawlPolicy.objects.order_by(
            models.Case(
                models.When(url_regex_pg=".*", then=models.Value(0)),
                default=models.Value(1),
                output_field=models.IntegerField(),
            ),
            "url_regex_pg",
        )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.url_regex == "(default)":
            return self.readonly_fields + ("url_regex", "enabled")
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            # Remove the "documents" field when the a object is new
            fieldsets[0][1]["fields"] = tuple(filter(lambda x: x != "documents", fieldsets[0][1]["fields"]))
        return fieldsets

    def has_delete_permission(self, request, obj=None):
        if obj and obj.url_regex == "(default)":
            return False
        return super().has_delete_permission(request, obj)

    @staticmethod
    def documents(obj):
        count = Document.objects.filter(url__regex=obj.url_regex_pg).count()
        params = urlencode({"q": obj.url_regex_pg})
        return format_html(
            '<a href="{}">Matching documents ({})</a>', reverse("admin:se_document_changelist") + "?" + params, count
        )

    @staticmethod
    def docs(obj):
        count = Document.objects.filter(url__regex=obj.url_regex_pg).count()
        params = urlencode({"q": obj.url_regex_pg})
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:se_document_changelist") + "?" + params,
            count,
        )

    @staticmethod
    @admin.display(description="Policy")
    def crawl_policy_desc(obj):
        return render_to_string(
            "admin/crawl_policy_desc.html",
            {
                "crawl_policy": obj,
                "CrawlPolicy": CrawlPolicy,
                "DomainSetting": DomainSetting,
                "label_tag": "label_tag_inline",
                "settings": settings,
            },
        )

    def get_search_results(self, request, queryset, search_term):
        if search_term.startswith("http://") or search_term.startswith("https://"):
            policy = CrawlPolicy.get_from_url(search_term, queryset)
            policies = CrawlPolicy.objects.filter(id=policy.id)
            return policies, False
        return super().get_search_results(request, queryset, search_term)


@admin.register(DomainSetting)
class DomainSettingAdmin(admin.ModelAdmin):
    list_display = ("domain", "ignore_robots", "robots_status", "browse_mode")
    search_fields = ("domain",)
    fields = (
        "domain",
        "documents",
        "browse_mode",
        "ignore_robots",
        "robots_status",
        "robots_allow",
        "robots_disallow",
    )
    readonly_fields = (
        "domain",
        "documents",
        "robots_status",
        "robots_allow",
        "robots_disallow",
    )

    def has_add_permission(self, request, obj=None):
        return False

    @staticmethod
    def documents(obj):
        params = urlencode({"q": f"^https?://{obj.domain}/"})
        return format_html(
            '<a href="{}">Matching documents</a>',
            reverse("admin:se_document_changelist") + "?" + params,
        )


class CookieForm(CharFieldForm):
    pass


@admin.register(Cookie)
class CookieAdmin(admin.ModelAdmin):
    list_display = ("domain", "domain_cc", "path", "name", "value", "expires")
    search_fields = ("domain", "path")
    ordering = ("domain", "domain_cc", "path", "name")
    form = CookieForm
    exclude = tuple()

    def get_search_results(self, request, queryset, search_term):
        if search_term.startswith("http://") or search_term.startswith("https://"):
            cookies = Cookie.get_from_url(search_term, queryset, expire=False)
            cookies = sorted(cookies, key=lambda x: x.name)
            _cookies = Cookie.objects.filter(id__in=[c.id for c in cookies])
            return _cookies, False
        return super().get_search_results(request, queryset, search_term)

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                "import/",
                self.admin_site.admin_view(self.cookies_import),
                name="cookies_import",
            ),
        ] + urls

    def cookies_import(self, request):
        from .cookies_import import CookiesImportView

        return CookiesImportView.as_view()(request)


class ExcludedUrlForm(CharFieldForm):
    TEXT_FIELDS = ("comment",)


@admin.register(ExcludedUrl)
class ExcludedUrlAdmin(admin.ModelAdmin):
    list_display = ("url",)
    search_fields = ("url", "comment")
    ordering = ("url",)
    form = ExcludedUrlForm


if settings.DEBUG:

    class HTMLAssetForm(CharFieldForm):
        pass

    @admin.register(HTMLAsset)
    class HTMLAssetAdmin(admin.ModelAdmin):
        list_display = ("url", "filename", "ref_count")
        search_fields = ("url", "filename")
        ordering = ("url", "filename", "ref_count")
        form = HTMLAssetForm
        exclude = tuple()

        def has_add_permission(self, request, obj=None):
            return False
