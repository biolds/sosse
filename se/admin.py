# Copyright 2022-2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import json
from copy import copy
from datetime import timedelta
from urllib.parse import quote_plus, urlencode

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, reverse
from django.template import defaultfilters
from django.template.loader import render_to_string
from django.urls import path
from django.utils.html import format_html, mark_safe
from django.utils.timezone import now
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .add_to_queue import AddToQueueView
from .analytics import AnalyticsView
from .collection import Collection
from .cookie import Cookie
from .crawl_queue import CrawlQueueContentView, CrawlQueueView
from .crawlers import CrawlersContentView, CrawlersView
from .document import Document
from .domain import Domain
from .html_asset import HTMLAsset
from .mime_plugin import MimePlugin
from .models import AuthField, ExcludedUrl, Link, SearchEngine, WorkerStats
from .tag import Tag
from .tag_field import TagField
from .utils import mimetype_icon, reverse_no_escape
from .webhook import Webhook, webhook_html_status


class SEAdminSite(admin.AdminSite):
    enable_nav_sidebar = False
    index_title = "Administration"

    MODEL_ICONS = {
        "Cookie": "🍪 ",
        "Collection": "⚡",
        "Tag": "⭐",
        "Document": "🔤 ",
        "Domain": "🕸",
        "Webhook": "📡",
        "MimePlugin": "🧩",
        "ExcludedUrl": "🔗",
        "SearchEngine": "🔍",
        "User": "👤",
        "Group": "👥",
    }

    def get_app_list(self, request):
        MODELS_ORDER = (
            (
                "se",
                (
                    "Collection",
                    "Tag",
                    "Document",
                    "Domain",
                    "Cookie",
                    "Webhook",
                    "MimePlugin",
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
                                dj_model["icon"] = self.MODEL_ICONS.get(model)
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

    def app_index(self, request, app_label, extra_context=None):
        return redirect("admin:index")


admin_site = SEAdminSite(name="admin")


def get_admin():
    global admin_site
    return admin_site


class ReturnUrlAdminMixin:
    def response_add(self, request, obj, post_url_continue=None):
        if "_continue" not in request.POST and "_addanother" not in request.POST:
            return_url = request.GET.get("return_url")
            if return_url:
                return HttpResponseRedirect(return_url)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if "_continue" not in request.POST and "_addanother" not in request.POST:
            return_url = request.GET.get("return_url")
            if return_url:
                return HttpResponseRedirect(return_url)
        return super().response_change(request, obj)


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


class InlineActionModelAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        view_name = f"do_{self.model._meta.app_label}_{self.model._meta.model_name}_action"
        return [
            path(
                "<path:object_id>/do_action/",
                self.admin_site.admin_view(self.do_action),
                name=view_name,
            ),
        ] + urls

    def do_action(self, request, object_id):
        if not request.user.has_perm(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}"):
            raise PermissionDenied

        action_name = request.POST.get("action")

        for action in self.actions:
            if action.__name__ == action_name:
                break
        else:
            raise Exception(f"Action {action_name} not supported ({self.actions})")

        queryset = self.get_queryset(request).filter(id=object_id)
        r = action(self, request, queryset)

        # Display a "Done" message if no other message was set
        if len(messages.get_messages(request)) == 0:
            messages.success(request, "Done.")

        if isinstance(r, HttpResponse):
            return r
        view_name = f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change"
        return redirect(reverse(view_name, args=(object_id,)))

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if extra_context is None:
            extra_context = {}
        action_url = reverse(
            f"admin:do_{self.model._meta.app_label}_{self.model._meta.model_name}_action", args=[object_id]
        )
        extra_context |= {"action_url": action_url, "actions": self.get_action_choices(request)}
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


class ConflictingSearchEngineFilter(admin.SimpleListFilter):
    title = "conflicting"
    parameter_name = "conflict"

    def lookups(self, request, model_admin):
        return (("yes", "Conflicting"),)

    @staticmethod
    def conflicts(queryset):
        return (
            SearchEngine.objects.exclude(enabled=False)
            .values("shortcut")
            .annotate(shortcut_count=models.Count("shortcut"))
            .filter(shortcut_count__gt=1)
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            conflicts = self.conflicts(queryset).values_list("shortcut")
            return queryset.filter(shortcut__in=conflicts)

        return queryset


@admin.action(description="Enable/Disable", permissions=["change"])
def search_engine_enable_disable(modeladmin, request, queryset):
    queryset.update(
        enabled=models.Case(
            models.When(enabled=True, then=models.Value(False)),
            models.When(enabled=False, then=models.Value(True)),
        )
    )


class BuiltinAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.builtin:
            fields = copy(self.get_fields(request))
            fields.remove("enabled")
            return fields
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.builtin:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(SearchEngine)
class SearchEngineAdmin(BuiltinAdmin):
    list_display = ("short_name", "enabled", "shortcut", "builtin")
    search_fields = ("short_name", "shortcut")
    readonly_fields = ("builtin",)
    list_filter = (
        "enabled",
        "builtin",
        ConflictingSearchEngineFilter,
    )
    actions = (search_engine_enable_disable,)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.builtin:
            fields = copy(self.get_fields(request))
            fields.remove("shortcut")
            fields.remove("enabled")
            return fields
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.builtin:
            return False
        return super().has_delete_permission(request, obj)


class DocumentStateFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "has_error"

    def lookups(self, request, model_admin):
        return (
            ("no", "Success"),
            ("yes", "Failure"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(error="")

        if self.value() == "no":
            return queryset.filter(error="")


class ActiveTagMixin:
    @staticmethod
    @admin.display(description="Tags")
    def active_tags(obj):
        model = obj.__class__._meta.model_name

        html = ""
        for tag in obj.tags.order_by("name"):
            tag.href = reverse(f"admin:se_{model}_changelist") + f"?tags={tag.id}"
            html += render_to_string(
                "se/components/tag.html",
                {"tag": tag, "suffix": f"-{model}-{obj.id}"},
            )

        return mark_safe(html)


class DocumentQueueFilter(admin.SimpleListFilter):
    title = "Queued"
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
            ("full", "No parent and children"),
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
            redirects_url = (
                Document.objects.w_content().filter(redirect_url__isnull=False).values_list("redirect_url", flat=True)
            )
            queryset = queryset.exclude(url__in=redirects_url)

        return queryset


class TagsFilter(admin.SimpleListFilter):
    title = "⭐ Tags"
    parameter_name = "tags"

    def lookups(self, request, model_admin):
        return [(tag.id, tag.path_name()) for tag in Tag.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tags__id=self.value()).distinct()
        return queryset


class CollectionFilter(admin.SimpleListFilter):
    title = "⚡ Collection"
    parameter_name = "collection"

    def lookups(self, request, model_admin):
        return [(collection.id, collection.name) for collection in Collection.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(collection__id=self.value())
        return queryset


@admin.action(description="Crawl now", permissions=["change"])
def crawl_now(modeladmin, request, queryset):
    queryset.update(crawl_next=now(), manual_crawl=True, retries=0)
    WorkerStats.wake_up()
    return redirect(reverse("admin:crawl_queue"))


@admin.action(description="Stop recrawl", permissions=["change"])
def remove_from_crawl_queue(modeladmin, request, queryset):
    queryset.update(crawl_next=None)


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


@admin.action(description="Trigger webhooks", permissions=["change"])
def trigger_webhooks(modeladmin, request, queryset):
    for doc in queryset.all():
        collection = doc.collection
        webhooks = collection.webhooks.all()
        Webhook.trigger(webhooks, doc)
        doc.save()


@admin.action(description="Clear tags", permissions=["change"])
def clear_tags(modeladmin, request, queryset):
    Document.tags.through.objects.filter(document__in=queryset).delete()


@admin.action(description="Move to collection", permissions=["change"])
def move_to_collection(modeladmin, request, queryset):
    request.session["documents_to_move"] = list(queryset.values_list("id", flat=True))
    return redirect(reverse("admin:move_to_collection"))


class DocumentForm(forms.ModelForm):
    collection = forms.ModelChoiceField(queryset=Collection.objects.all(), widget=forms.Select(), empty_label=None)

    class Meta:
        model = Document
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        self.fields["tags"] = TagField(model=Document, instance=instance)


@admin.register(Document)
class DocumentAdmin(InlineActionModelAdmin, ActiveTagMixin):
    form = DocumentForm
    list_display = (
        "_url",
        "collection",
        "status",
        "_title",
        "active_tags",
        "err",
        "_crawl_last",
        "_crawl_next",
        "_modified_date",
        "crawl_dt",
    )
    list_filter = (
        DocumentQueueFilter,
        DocumentStateFilter,
        CollectionFilter,
        "show_on_homepage",
        TagsFilter,
        "hidden",
        DocumentOrphanFilter,
        "crawl_last",
    )
    search_fields = ["url__regex", "title__regex"]
    ordering = ("-crawl_last",)
    actions = [
        crawl_now,
        remove_from_crawl_queue,
        clear_tags,
        switch_hidden,
        trigger_webhooks,
        move_to_collection,
    ]
    if settings.DEBUG:
        actions += [crawl_later]
    list_per_page = settings.SOSSE_ADMIN_PAGE_SIZE

    fieldsets = (
        (
            "📖 Main",
            {
                "fields": (
                    "_title",
                    "collection",
                    "tags",
                    "related",
                    "show_on_homepage",
                    "hidden",
                    "_status",
                    "_robotstxt_rejected",
                    "too_many_redirects",
                )
            },
        ),
        (
            "📂 Content",
            {
                "fields": (
                    "_mimetype",
                    "_lang_txt",
                    "_content",
                )
            },
        ),
        (
            "🕑 Crawl time",
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
        (
            "🧩 Mime Handlers",
            {
                "fields": (
                    "_mimetype2",
                    "mime_plugins_result",
                ),
            },
        ),
        (
            "📡 Webhooks",
            {
                "fields": ("_webhooks_result",),
            },
        ),
        (
            "📊 Metadata",
            {
                "fields": ("_metadata",),
            },
        ),
    )
    readonly_fields = [
        "_title",
        "related",
        "_status",
        "_robotstxt_rejected",
        "too_many_redirects",
        "_mimetype",
        "_mimetype2",
        "_lang_txt",
        "_content",
        "crawl_first",
        "mime_plugins_result",
        "modified_date",
        "_crawl_last_txt",
        "_crawl_next_txt",
        "crawl_dt",
        "crawl_recurse",
        "_webhooks_result",
        "_metadata",
    ]

    class Media:
        js = ("se/tags.js",)

    def get_queryset(self, request):
        return Document.objects.w_content()

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        return [
            path("analytics/", self.admin_site.admin_view(self.analytics), name="analytics"),
            path("queue/", self.admin_site.admin_view(self.add_to_queue), name="queue"),
            path(
                "move_to_collection/",
                self.admin_site.admin_view(self.move_to_collection_view),
                name="move_to_collection",
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

    def get_fields(self, request, obj=None):
        fields = copy(super().get_fields(request, obj))
        if not settings.SOSSE_BROWSABLE_HOME:
            fields.remove("show_on_homepage")
        return fields

    def lookup_allowed(self, lookup, value):
        if lookup in ("linked_from__doc_from", "links_to__doc_to"):
            return True
        return super().lookup_allowed(lookup, value)

    def add_to_queue(self, request):
        return AddToQueueView.as_view(admin_site=self.admin_site)(request)

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

    def move_to_collection_view(self, request):
        from .move_to_collection import MoveToCollectionView

        return MoveToCollectionView.as_view(admin_site=self.admin_site)(request)

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
    def related(obj):
        try:
            collection = obj.collection
            policy = format_html(
                '⚡&nbsp<a href="{}">Collection&nbsp{}</a>',
                reverse("admin:se_collection_change", args=(collection.id,)),
                collection,
            )

            tags_count = obj.tags.count()
            tags_url = reverse("admin:se_tag_changelist") + f"?document={obj.id}"
            tags = format_html('⭐&nbsp<a href="{}">Tags ({})</a>', tags_url, tags_count)

            domain = Domain.get_from_url(obj.url)
            domain_link = format_html(
                '🕸&nbsp<a href="{}">Domain {}</a>',
                reverse("admin:se_domain_change", args=(domain.id,)),
                domain.domain,
            )

            cookies = format_html(
                '🍪&nbsp<a href="{}">Cookies ({})</a>',
                reverse("admin:se_cookie_changelist") + "?q=" + quote_plus(obj.url),
                Cookie.objects.filter(domain=domain.domain).count(),
            )

            source = obj.get_source_link()
            archive = format_html('🔖&nbsp<a href="{}">Archive</a>', obj.get_absolute_url())

            links_to_here_url = reverse("admin:se_document_changelist") + f"?links_to__doc_to={obj.id}"
            links_to_here = format_html('🔗&nbsp<a href="{}">Links to here</a>', links_to_here_url)

            links_from_here_url = reverse("admin:se_document_changelist") + f"?linked_from__doc_from={obj.id}"
            links_from_here = format_html('🔗&nbsp<a href="{}">Links from here</a>', links_from_here_url)

            return format_html(
                '<p style="margin-top: 0"><span>{}</span></p>'
                '<p><span>{}</span><span class="label_tag">{}</span><br></p>'
                '<p><span>{}</span><span class="label_tag">{}</span><br></p>'
                '<p><span>{}</span><span class="label_tag">{}</span><span class="label_tag">{}</span></p>',
                archive,
                policy,
                domain_link,
                tags,
                cookies,
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
    @admin.display(description="Robots.txt status")
    def _robotstxt_rejected(obj):
        domain = Domain.get_from_url(obj.url)
        if obj.robotstxt_rejected:
            return format_html(
                '<img src="{}" alt="Rejected" title="Rejected" /> 🤖 Rejected by robots.txt file, see corresponding 🕸 <a href="{}">Domain</a>',
                f"{settings.STATIC_URL}admin/img/icon-no.svg",
                reverse("admin:se_domain_change", args=(domain.id,)),
            )

        return format_html(
            '<img src="{}" alt="Accepted" /> Accepted, see corresponding 🕸 <a href="{}">Domain</a>',
            f"{settings.STATIC_URL}admin/img/icon-yes.svg",
            reverse("admin:se_domain_change", args=(domain.id,)),
        )

    @staticmethod
    @admin.display(description="Mimetype")
    def _mimetype(obj):
        icon = mimetype_icon(obj.mimetype)
        value = format_html(f"{icon} {obj.mimetype}")

        plugins = MimePlugin.objects.extra(where=["%s ~ mimetype_re"], params=[obj.mimetype])
        if plugins.exists():
            value += format_html(
                ' <a href="{}" style="margin-left: 10px">🧩 Plugins ({})</a>',
                reverse("admin:se_mimeplugin_changelist") + f"?q={obj.mimetype}",
                plugins.count(),
            )
        return value

    # Duplicate field since django won't accept referencing it twice
    _mimetype2 = _mimetype

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

    @staticmethod
    @admin.display(description="Results")
    def _webhooks_result(obj):
        status = []
        if obj.webhooks_result == {}:
            collection = obj.collection
            if collection.webhooks.count() == 0:
                return format_html(
                    "Matching ⚡ Collection <a href={}>{}</a> has no 📡 Webhooks.",
                    reverse("admin:se_collection_change", args=(collection.id,)),
                    collection,
                )
            return "No webhook was triggered yet."

        for webhook_id, result in obj.webhooks_result.items():
            try:
                webhook = Webhook.objects.get(id=webhook_id)
            except Webhook.DoesNotExist:
                status.append(
                    format_html(
                        "<div><p>📡 Deleted webhook</p><p>{}</p></div>\n",
                        webhook_html_status(result),
                    )
                )
            else:
                status.append(
                    format_html(
                        '<div><p>📡 <a href="{}">Webhook {}</a></p><p>{}</p></div>\n',
                        reverse("admin:se_webhook_change", args=(webhook.id,)),
                        webhook.name,
                        webhook_html_status(result),
                    )
                )
        return mark_safe("\n".join(status))

    def _metadata(self, obj):
        metadata = obj.metadata
        if not metadata:
            return "No metadata"

        formatted_json = json.dumps(metadata, indent=2, sort_keys=True)
        return format_html('<pre style="white-space: pre-wrap;">{}</pre>', formatted_json)

    def delete_model(self, request, obj):
        obj.delete_all()
        return super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset.all():
            obj.delete_all()
        return super().delete_queryset(request, queryset)


class InlineAuthField(admin.TabularInline):
    model = AuthField


class CollectionForm(CharFieldForm):
    TEXT_FIELDS = ("unlimited_regex", "limited_regex", "excluded_regex", "script")

    webhooks = forms.ModelMultipleChoiceField(
        queryset=Webhook.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple("Webhooks", is_stacked=False),
        required=False,
    )

    queue_to_collections = forms.ModelMultipleChoiceField(
        queryset=Collection.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple("Collections", is_stacked=False),
        required=False,
    )

    class Meta:
        model = Collection
        exclude = tuple()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        self.fields["tags"] = TagField(model=Collection, instance=instance)

        # Exclude self from queue_to_collections choices
        if instance and instance.pk:
            self.fields["queue_to_collections"].queryset = Collection.objects.exclude(pk=instance.pk)

        for field in ("unlimited_regex", "limited_regex", "excluded_regex"):
            # Fields are empty when the form is readonly
            if field in self.fields:
                self.fields[field].widget.attrs["rows"] = 5

    def clean(self):
        cleaned_data = super().clean()

        keys_required = {
            "recrawl_dt_min": cleaned_data["recrawl_freq"]
            in (Collection.RECRAWL_FREQ_ADAPTIVE, Collection.RECRAWL_FREQ_CONSTANT),
            "recrawl_dt_max": cleaned_data["recrawl_freq"] in (Collection.RECRAWL_FREQ_ADAPTIVE,),
        }

        for key, required in keys_required.items():
            if required and cleaned_data.get(key) is None:
                self.add_error(key, "This field is required when using this recrawl mode")

            if not required and cleaned_data.get(key) is not None:
                self.add_error(key, "This field must be null when using this recrawl mode")

        if cleaned_data["default_browse_mode"] not in (
            Domain.BROWSE_CHROMIUM,
            Domain.BROWSE_FIREFOX,
        ):
            if cleaned_data["thumbnail_mode"] in (
                Collection.THUMBNAIL_MODE_SCREENSHOT,
                Collection.THUMBNAIL_MODE_PREV_OR_SCREEN,
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


@admin.action(description="Duplicate", permissions=["change"])
def collection_duplicate(modeladmin, request, queryset):
    for collection in queryset.all():
        tags = list(collection.tags.all())
        webhooks = list(collection.webhooks.all())
        collection.id = None
        collection.name = f"Copy of {collection.name}"
        collection.save()
        collection.tags.set(tags)
        collection.webhooks.set(webhooks)
        msg = format_html(
            "Collection <a href='{}'>{}</a> created.",
            reverse("admin:se_collection_change", args=(collection.id,)),
            collection,
        )
        messages.success(request, msg)


@admin.action(description="Update doc tags", permissions=["document_change"])
def update_doc_tags(modeladmin, request, queryset, clear_first=False):
    for obj in queryset:
        documents = Document.objects.wo_content().filter(url__regex=obj.unlimited_regex_pg)

        if clear_first:
            Document.tags.through.objects.filter(document__in=documents).delete()

        tags = obj.tags.all()
        documents_id = documents.values_list("id", flat=True)
        new_tags = [(doc_id, tag.id) for doc_id in documents_id for tag in tags]

        if new_tags:
            Document.tags.through.objects.bulk_create(
                [Document.tags.through(document_id=doc_id, tag_id=tag_id) for doc_id, tag_id in new_tags],
                ignore_conflicts=True,
            )


@admin.action(description="Clear & update doc tags", permissions=["document_change"])
def clear_update_doc_tags(modeladmin, request, queryset):
    update_doc_tags(modeladmin, request, queryset, True)


@admin.register(Collection)
class CollectionAdmin(ReturnUrlAdminMixin, InlineActionModelAdmin, ActiveTagMixin):
    inlines = [InlineAuthField]
    form = CollectionForm
    list_display = (
        "name",
        "active_tags",
        "docs",
        "collection_desc",
    )
    list_filter = (TagsFilter,)
    search_fields = (
        "name",
        "unlimited_regex",
    )
    readonly_fields = ("related", "webhooks_link")
    fieldsets = (
        (
            "⚡ Crawl",
            {
                "fields": (
                    "name",
                    "related",
                    "unlimited_regex",
                    "limited_regex",
                    "recursion_depth",
                    "excluded_regex",
                    "tags",
                    "mimetype_regex",
                    "keep_params",
                    "store_extern_links",
                    "hide_documents",
                    "remove_nav_elements",
                    "thumbnail_mode",
                    "queue_to_any_collection",
                    "queue_to_collections",
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
                    "recrawl_freq",
                    "recrawl_dt_min",
                    "recrawl_dt_max",
                    "hash_mode",
                    "recrawl_condition",
                )
            },
        ),
        (
            "🔒 Authentication",
            {
                "fields": ("auth_login_url_re", "auth_form_selector"),
            },
        ),
        (
            "📡 Webhooks",
            {
                "fields": (
                    "webhooks_link",
                    "webhooks",
                ),
            },
        ),
    )
    actions = [collection_duplicate, update_doc_tags, clear_update_doc_tags]

    class Media:
        js = ("se/tags.js", "se/admin-collection.js")

    def changelist_view(self, request, extra_context=None):
        Collection.create_default()
        return super().changelist_view(request, extra_context)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            # Remove the "documents" field when the a object is new
            fieldsets[0][1]["fields"] = tuple(filter(lambda x: x != "documents", fieldsets[0][1]["fields"]))
        return fieldsets

    def has_document_change_permission(self, request, obj=None):
        return request.user.has_perm("se.document_change")

    @staticmethod
    def related(obj):
        doc_count = Document.objects.wo_content().filter(collection=obj).count()
        docs = format_html(
            '<a href="{}">🔤&nbspDocuments ({})</a>',
            reverse("admin:se_document_changelist") + f"?collection={obj.id}",
            doc_count,
        )

        tag_count = obj.tags.count()
        tags = format_html(
            '<a href="{}">⭐&nbspTags ({})</a>',
            reverse("admin:se_tag_changelist") + f"?collection={obj.id}",
            tag_count,
        )
        return format_html(
            '<p style="margin-top: 0"><span>{}</span><span class="label_tag">{}</span><br></p>', docs, tags
        )

    @staticmethod
    def docs(obj):
        doc_count = Document.objects.wo_content().filter(collection=obj).count()
        return format_html(
            '🔤 <a href="{}">{}</a>',
            reverse("admin:se_document_changelist") + f"?collection={obj.id}",
            doc_count,
        )

    @staticmethod
    @admin.display(description="Policy")
    def collection_desc(obj):
        return render_to_string(
            "admin/collection_desc.html",
            {
                "collection": obj,
                "Collection": Collection,
                "Domain": Domain,
                "label_tag": "label_tag_inline",
                "settings": settings,
            },
        )

    @staticmethod
    @admin.display(description="Edit")
    def webhooks_link(obj):
        if not Webhook.objects.count():
            return format_html('<a href="{}">Create a Webhook</a>', reverse("admin:se_webhook_add"))
        elif not obj or not obj.webhooks.count():
            return format_html('<a href="{}">Edit Webhooks</a>', reverse("admin:se_webhook_changelist"))

        webhooks = reverse("admin:se_webhook_changelist") + f"?collection={obj.id}"
        return format_html('<a href="{}">Edit Webhooks</a>', webhooks)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
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

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs, labels={"ignore_robots": "🤖 Ignore robots.txt"})
        return form

    def has_add_permission(self, request, obj=None):
        return False

    @staticmethod
    def documents(obj):
        params = urlencode({"q": f"^https?://{obj.domain}/"})
        count = Document.objects.wo_content().filter(url__regex=f"^https?://{obj.domain}/").count()
        return format_html(
            '<a href="{}">Matching 🔤 Documents ({})</a>', reverse("admin:se_document_changelist") + "?" + params, count
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

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                "import/",
                self.admin_site.admin_view(self.excluded_urls_import),
                name="excluded_urls_import",
            ),
        ] + urls

    def excluded_urls_import(self, request):
        from .excluded_urls_import import ExcludedUrlsImportView

        return ExcludedUrlsImportView.as_view()(request)


BaseTagForm = movenodeform_factory(Tag)


class TagForm(BaseTagForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["_ref_node_id"].label = "Parent"
        self.fields["_position"].widget = forms.HiddenInput()
        self.fields["_position"].initial = "sorted-child"


@admin.register(Tag)
class TagAdmin(ReturnUrlAdminMixin, TreeAdmin):
    form = TagForm
    list_display = ("_name", "docs", "policies", "webhooks_count")
    fields = ("name", "_ref_node_id", "documents", "collections", "webhooks", "_position")
    readonly_fields = ("documents", "collections", "webhooks")
    search_fields = ("name",)

    @staticmethod
    def _name(obj):
        return render_to_string("se/components/tag.html", {"tag": obj})

    @staticmethod
    def documents(obj):
        if not obj or not obj.id:
            return ""
        count = Document.objects.wo_content().filter(tags__id=obj.id).count()
        return format_html(
            '<a href="{}">Matching 🔤 Documents ({})</a>',
            reverse("admin:se_document_changelist") + f"?tags={obj.id}",
            count,
        )

    @staticmethod
    def docs(obj):
        count = Document.objects.wo_content().filter(tags__id=obj.id).count()
        return format_html(
            '🔤 <a href="{}">{}</a>',
            reverse("admin:se_document_changelist") + f"?tags={obj.id}",
            count,
        )

    @staticmethod
    @admin.display(description="Collections")
    def collections(obj):
        if not obj or not obj.id:
            return ""
        count = Collection.objects.filter(tags__id=obj.id).count()
        return format_html(
            '<a href="{}">Used in ⚡ Collections ({})</a>',
            reverse("admin:se_collection_changelist") + f"?tags={obj.id}",
            count,
        )

    @staticmethod
    @admin.display(description="Collections")
    def policies(obj):
        count = Collection.objects.filter(tags__id=obj.id).count()
        return format_html(
            '⚡ <a href="{}">{}</a>',
            reverse("admin:se_collection_changelist") + f"?tags={obj.id}",
            count,
        )

    @staticmethod
    @admin.display(description="Webhooks")
    def webhooks(obj):
        if not obj or not obj.id:
            return ""
        count = Webhook.objects.filter(tags__id=obj.id).count()
        return format_html(
            '<a href="{}">Used in 📡 Webhooks ({})</a>',
            reverse("admin:se_collection_changelist") + f"?tags={obj.id}",
            count,
        )

    @staticmethod
    @admin.display(description="Webhooks")
    def webhooks_count(obj):
        count = Webhook.objects.filter(tags__id=obj.id).count()
        return format_html(
            '📡 <a href="{}">{}</a>',
            reverse("admin:se_collection_changelist") + f"?tags={obj.id}",
            count,
        )


class WebhookForm(forms.ModelForm):
    # Force use a regular CharField for the URL field
    url = forms.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        model_field = self._meta.model._meta.get_field("tags")
        self.fields["tags"] = TagField(model=Webhook, instance=instance, help_text=model_field.help_text)
        self.fields["url"].widget.attrs.update({"style": "width: 48em"})

    class Meta:
        model = Webhook
        fields = "__all__"


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin, ActiveTagMixin):
    list_display = ("name", "enabled", "collections_count", "active_tags", "url", "trigger_condition")
    list_filter = ("enabled",)
    search_fields = ("name", "url", "trigger_condition")
    ordering = ("name",)
    fields = (
        "name",
        "collections_link",
        "enabled",
        "tags",
        "trigger_condition",
        "url",
        "updates_doc",
        "update_json_path",
        "update_json_deserialize",
        "body_template",
        "method",
        "headers",
        "username",
        "password",
        "url_re",
        "mimetype_re",
        "title_re",
        "content_re",
        "webhook_test",
    )
    readonly_fields = (
        "collections_link",
        "webhook_test",
    )
    form = WebhookForm

    class Media:
        js = ("se/admin-webhooks.js", "se/tags.js")

    @staticmethod
    @admin.display(description="Collections")
    def collections_count(obj):
        collections_count = obj.collection_set.count()
        webhooks = reverse("admin:se_collection_changelist") + f"?webhooks={obj.id}"
        return format_html('⚡ <a href="{}">{}</a>', webhooks, collections_count)

    @staticmethod
    @admin.display(description="Collections")
    def collections_link(obj):
        collections_count = 0
        if obj and obj.id:
            collections_count = obj.collection_set.count()

        if not collections_count:
            return format_html(
                '<a href="{}">No Collections use this Webhook</a>', reverse("admin:se_collection_changelist")
            )

        webhooks = reverse("admin:se_collection_changelist") + f"?webhooks={obj.id}"
        return format_html('<a href="{}">Edit Collections ({})</a>', webhooks, collections_count)

    def webhook_test(self, obj):
        return format_html(
            '<button id="webhook_test_button" class="button" type="button" onclick="test_webhook()">Trigger</button>'
        )

    webhook_test.short_description = "Webhook test"


@admin.register(MimePlugin)
class MimePluginAdmin(BuiltinAdmin):
    list_display = (
        "name",
        "enabled",
        "docs",
        "mimetype_re",
    )
    list_filter = ("enabled",)
    search_fields = (
        "name",
        "mimetype_re",
        "script",
    )
    fieldsets = (
        (
            None,
            {"fields": ("name", "enabled", "related", "mimetype_re", "script", "timeout")},
        ),
    )
    readonly_fields = ("related",)

    def get_search_results(self, request, queryset, search_term):
        queryset, _ = super().get_search_results(request, queryset, search_term)
        if search_term.strip():
            queryset = MimePlugin.objects.extra(where=["%s ~ mimetype_re"], params=[search_term.strip()])
        return queryset, False

    @staticmethod
    def related(obj):
        doc_count = Document.objects.wo_content().filter(mimetype__regex=obj.mimetype_re).count()
        params = urlencode({"mimetype__regex": obj.mimetype_re})
        return format_html(
            '<a href="{}">🔤&nbspDocuments ({})</a>', reverse("admin:se_document_changelist") + "?" + params, doc_count
        )

    @staticmethod
    def docs(obj):
        count = Document.objects.wo_content().filter(mimetype__regex=obj.mimetype_re).count()
        params = urlencode({"mimetype__regex": obj.mimetype_re})
        return format_html(
            '<a href="{}">🔤 {}</a>',
            reverse("admin:se_document_changelist") + "?" + params,
            count,
        )


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
