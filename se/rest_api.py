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

import logging
import os

from django.conf import settings
from django.db import connection, models
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiTypes,
    extend_schema,
    extend_schema_field,
    extend_schema_serializer,
)
from rest_framework import mixins, routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.validators import ValidationError

from .browser import SkipIndexing
from .document import Document, example_doc
from .models import CrawlerStats
from .rest_permissions import DjangoModelPermissionsRW, IsSuperUserOrStaff
from .search import get_documents
from .search_form import FILTER_FIELDS, SORT, SearchForm
from .tag import Tag
from .utils import mimetype_icon
from .webhook import Webhook, webhook_html_status

webhook_logger = logging.getLogger("webhooks")


class CrawlerStatsSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = CrawlerStats


class CrawlerStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CrawlerStats.objects.order_by("t")
    serializer_class = CrawlerStatsSerializer
    filterset_fields = ("freq",)
    permission_classes = [IsSuperUserOrStaff]


class HddStatsSerializer(serializers.Serializer):
    db = serializers.IntegerField(help_text="Size of the database")
    screenshots = serializers.IntegerField(help_text="Size of the screenshots")
    html = serializers.IntegerField(help_text="Size of HTML dumps")
    other = serializers.IntegerField(help_text="Data not used by Sosse")
    free = serializers.IntegerField(help_text="Free space")


class HddStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    def dir_size(self, d):
        # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
        size = 0
        for dirpath, dirnames, filenames in os.walk(d):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    size += os.path.getsize(fp)
        return size

    @extend_schema(
        description="HDD analytics",
        responses={
            200: HddStatsSerializer(),
        },
    )
    def list(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_database_size(%s)", [settings.DATABASES["default"]["NAME"]])
            db_size = cursor.fetchall()[0][0]

        statvfs = os.statvfs("/var/lib")
        hdd_size = statvfs.f_frsize * statvfs.f_blocks
        hdd_free = statvfs.f_frsize * statvfs.f_bavail

        screenshot_size = self.dir_size(settings.SOSSE_SCREENSHOTS_DIR)
        html_size = self.dir_size(settings.SOSSE_HTML_SNAPSHOT_DIR)
        hdd_other = hdd_size - hdd_free - db_size - screenshot_size - html_size
        return Response(
            {
                "db": db_size,
                "screenshots": screenshot_size,
                "html": html_size,
                "other": hdd_other,
                "free": hdd_free,
            }
        )


class LangStatsSerializer(serializers.Serializer):
    doc_count = serializers.IntegerField(help_text="Document count")
    lang = serializers.CharField(help_text="Language")


class LangStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    @extend_schema(
        description="HDD analytics",
        responses={
            200: LangStatsSerializer(many=True),
        },
    )
    def list(self, request):
        langs = []
        indexed_langs = (
            Document.objects.wo_content()
            .exclude(lang_iso_639_1__isnull=True)
            .values("lang_iso_639_1")
            .annotate(count=models.Count("lang_iso_639_1"))
            .order_by("-count")
        )
        if indexed_langs:
            for lang in indexed_langs:
                lang_iso = lang["lang_iso_639_1"]
                lang_desc = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {})
                title = lang_iso.title()
                if lang_desc.get("flag"):
                    title = title + " " + lang_desc["flag"]
                langs.append({"lang": title, "doc_count": lang["count"]})
        return Response(langs)


class MimeStatsSerializer(serializers.Serializer):
    doc_count = serializers.IntegerField(help_text="Document count")
    mime = serializers.CharField(help_text="Mimetype")


class MimeStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    @extend_schema(
        description="Mimetype analytics",
        responses={
            200: MimeStatsSerializer(many=True),
        },
    )
    def list(self, request):
        indexed_mimes = (
            Document.objects.wo_content()
            .annotate(
                mimetype_coalesced=Coalesce("mimetype", models.Value("NULL"))
            )  # Coalesce otherwise PG does not count NULL values
            .values("mimetype_coalesced")
            .annotate(doc_count=models.Count("*"))
            .order_by("-doc_count", "mimetype")
        )

        indexed_mimes = {a["mimetype_coalesced"]: a["doc_count"] for a in indexed_mimes}
        null_count = indexed_mimes.pop("NULL", 0)

        if null_count:
            indexed_mimes[""] = indexed_mimes.get("", 0) + null_count

        indexed_mimes = sorted(
            [{"mimetype": mime, "doc_count": count} for mime, count in indexed_mimes.items()],
            key=lambda x: -x["doc_count"],
        )

        for indexed_mime in indexed_mimes:
            mimetype = indexed_mime["mimetype"]
            icon = mimetype_icon(mimetype)
            if mimetype:
                indexed_mime["mimetype"] = f"{icon} {mimetype}"
            else:
                indexed_mime["mimetype"] = f"{icon} <None>"

        return Response(indexed_mimes)


class TagSlugRelatedField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        if isinstance(data, int):
            return Tag.objects.get(pk=data)

        tag, _ = Tag.objects.get_or_create(name=data)
        return tag


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = "__all__"
        read_only_fields = (
            "url",
            "normalized_url",
            "normalized_title",
            "normalized_content",
            "content_hash",
            "favicon",
            "robotstxt_rejected",
            "has_html_snapshot",
            "redirect_url",
            "too_many_redirects",
            "screenshot_count",
            "screenshot_format",
            "screenshot_size",
            "has_thumbnail",
            "crawl_first",
            "crawl_last",
            "crawl_next",
            "crawl_dt",
            "crawl_recurse",
            "modified_date",
            "manual_crawl",
            "error",
            "error_hash",
            "worker_no",
        )

    tags = TagSlugRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field="name",
    )

    tags_str = serializers.SerializerMethodField()

    def get_tags_str(self, obj):
        if obj.id:
            # Accessing obj.tags thru many-to-many relation requires the object to exist
            return ", ".join([tag.name for tag in obj.tags.order_by("name")])
        return ""

    def user_doc_update(self, ctx_msg):
        try:
            self.is_valid(raise_exception=True)
            self.update(self.instance, self.validated_data)
        except ValidationError as e:
            raise SkipIndexing(f"{ctx_msg} result validation error:\n{e.detail}\nInput data was:\n{self.data}\n---")
        except Exception as e:
            msg = f"{ctx_msg} document update error:\n{e.args[0]}\nInput data was:\n{self.data}\n---"
            e.args = (msg,) + e.args[1:]
            raise e

    def validate(self, attrs):
        attrs = super().validate(attrs)
        title = attrs.get("title")
        if title is not None:
            attrs["normalized_title"] = Document._normalized_title(title)
        content = attrs.get("content")
        if content is not None:
            attrs["normalized_content"] = Document._normalized_content(content)
        return attrs


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.w_content()
    serializer_class = DocumentSerializer
    permission_classes = [DjangoModelPermissionsRW]

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")


class SearchAdvancedQuery(serializers.Serializer):
    field = serializers.ChoiceField(choices=FILTER_FIELDS, default="doc", help_text="Field to filter on")
    type = serializers.ChoiceField(
        choices=(("inc", "Include"), ("exc", "Exclude")),
        default="inc",
        help_text="Type of filter",
    )
    OP_CHOICES = ("contain", "regexp", "equal")
    operator = serializers.ChoiceField(
        choices=list(zip(OP_CHOICES, OP_CHOICES)),
        default="contain",
        help_text="Filtering operator",
    )
    case_sensitive = serializers.BooleanField(default=False)
    term = serializers.CharField(help_text="Filtering terms")

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return {
            "ft": data["type"],
            "ff": data["field"],
            "fo": data["operator"],
            "fv": data["term"],
            "fc": data["case_sensitive"],
        }


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Simple search query",
            value={
                "query": "big cats",
            },
        ),
        OpenApiExample(
            "Advanced search query",
            value={
                "query": "big cats",
                "adv_params": [
                    {
                        "field": "url",
                        "term": "https://wikipedia.org/",
                    }
                ],
            },
        ),
    ]
)
class SearchQuery(serializers.Serializer):
    query = serializers.CharField(default="", allow_blank=True, help_text="Search terms")
    lang = serializers.ChoiceField(
        default="en",
        choices=[(key, val["name"].title()) for key, val in settings.SOSSE_LANGDETECT_TO_POSTGRES.items()],
        help_text="Search terms language",
    )
    sort = serializers.ChoiceField(default="-rank", choices=SORT, help_text="Results sorting")
    include_hidden = serializers.BooleanField(
        default=False,
        help_text='Include hidden documents, requires the permission "Can change documents"',
    )
    adv_params = SearchAdvancedQuery(many=True, default=[], help_text="Advanced search parameters")

    def validate(self, data):
        data = super().validate(data)
        if not data.get("adv_params") and not data.get("query"):
            raise serializers.ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: 'At least "query" or "adv_params" field must be provided.'}
            )
        return data


class SearchResult(DocumentSerializer):
    url = serializers.CharField(help_text="Document URL")
    title = serializers.CharField(help_text="Document Title")
    score = serializers.SerializerMethodField(
        allow_null=True, help_text="Score of the document for provided search terms"
    )

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_score(self, obj):
        return getattr(obj, "rank", 1.0)


class SearchViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    @extend_schema(
        request=SearchQuery,
        description="Search queries",
        responses={
            200: SearchResult(many=True),
        },
    )
    def create(self, request, *args, **kwargs):
        query = SearchQuery(data=request.data)
        query.is_valid(raise_exception=True)
        f = SearchForm(
            data={
                "q": query.validated_data["query"],
                "l": query.validated_data["lang"],
                "s": query.validated_data["sort"],
                "i": "on" if query.validated_data["include_hidden"] else "",
            }
        )
        f.is_valid()
        _, documents, _ = get_documents(request, query.validated_data["adv_params"], f, False)
        page = self.paginate_queryset(documents)
        serializer = SearchResult(page, many=True)
        return self.get_paginated_response(serializer.data)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permissions = [DjangoModelPermissionsRW]

    @action(detail=False)
    def tree_doc_counts(self, request):
        return Response(Tag.tree_doc_counts())


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = "__all__"


class WebhookTestTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        exclude = ("name",)


class WebhookViewSet(viewsets.ModelViewSet):
    queryset = Webhook.objects.all()
    serializer_class = WebhookSerializer
    permissions = [DjangoModelPermissionsRW]

    @action(detail=False, methods=["post"])
    def test_trigger(self, request):
        as_html = request.GET.get("as_html")
        serializer = WebhookTestTriggerSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            webhook = Webhook(**serializer.validated_data)
            result = webhook.send(example_doc())
        except ValueError as e:
            webhook_logger.exception("Webhook error")
            if not as_html:
                return Response({"error": str(e)}, status=400)
            result = {"error": str(e)}
        except ValidationError as e:
            result = {"error": f"Webhook configuration error:\n{e.detail}"}

        if request.GET.get("as_html"):
            return HttpResponse(webhook_html_status(result))
        return Response(result)


router = routers.DefaultRouter()
router.register("document", DocumentViewSet)
router.register("tag", TagViewSet)
router.register("search", SearchViewSet, basename="search")
router.register("stats", CrawlerStatsViewSet)
router.register("hdd_stats", HddStatsViewSet, basename="hdd_stats")
router.register("lang_stats", LangStatsViewSet, basename="lang_stats")
router.register("mime_stats", MimeStatsViewSet, basename="mime_stats")
router.register("webhook", WebhookViewSet, basename="webhook")
