# Copyright 2025 Laurent Defert
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

from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import models
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiTypes,
    extend_schema,
    extend_schema_field,
    extend_schema_serializer,
)
from rest_framework import mixins, serializers, viewsets
from rest_framework.settings import api_settings

from ..collection import Collection
from ..document import Document, remove_accent
from ..search import add_headlines
from ..search_form import FILTER_FIELDS, SORT
from ..tag import Tag
from .document import DocumentSerializer

logger = logging.getLogger("web")


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
                "collection": 1,
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
class SearchQuerySerializer(serializers.Serializer):
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
    collection = serializers.IntegerField(required=False, help_text="Filter by collection ID")
    adv_params = SearchAdvancedQuery(many=True, default=[], help_text="Advanced search parameters")
    show_on_homepage = serializers.BooleanField(
        default=False,
        help_text="Filter documents shown on homepage",
    )
    robotstxt_rejected = serializers.BooleanField(
        required=False,
        help_text="Filter documents rejected by robots.txt",
    )
    has_error = serializers.BooleanField(
        required=False,
        help_text="Filter documents with errors",
    )

    def validate(self, data):
        data = super().validate(data)

        # Check if user has write permission on documents (admin)
        request = self.context["request"]
        has_write_permission = request.user.has_perm("se.change_document")

        # Non-admin users must provide query, adv_params or show_on_homepage
        if not has_write_permission:
            if not data.get("adv_params") and not data.get("query") and not data.get("show_on_homepage"):
                raise serializers.ValidationError(
                    {
                        api_settings.NON_FIELD_ERRORS_KEY: 'At least "query", "adv_params" or "show_on_homepage" field must be provided.'
                    }
                )

        collection_id = data.get("collection")
        if collection_id:
            try:
                Collection.objects.get(id=collection_id)
            except Collection.DoesNotExist:
                raise serializers.ValidationError({"collection": f"Collection with id {collection_id} does not exist."})

        # Normalize and validate language (from SearchForm.clean)
        lang_iso = data.get("lang", "en")
        pg_lang = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get("name")

        if pg_lang not in Document.get_supported_langs():
            pg_lang = settings.SOSSE_FAIL_OVER_LANG

        data["lang"] = pg_lang

        # Strip search query if configured (from SearchForm.clean)
        if settings.SOSSE_SEARCH_STRIP:
            q = data["query"]
            if q.startswith(settings.SOSSE_SEARCH_STRIP):
                q = q[len(settings.SOSSE_SEARCH_STRIP) :]
            if q.endswith(settings.SOSSE_SEARCH_STRIP):
                q = q[: -len(settings.SOSSE_SEARCH_STRIP)]
            data["query"] = q

        # Calculate order_by based on query and sort (from SearchForm.clean)
        q = data["query"]
        sort = data["sort"]

        if q:
            order_by = ("-rank", "title")
        else:
            order_by = ("title",)

        _order = sort
        if _order.startswith("-"):
            _order = _order[1:]

        if _order == "rank":
            if q:
                order_by = (sort, "title")
        elif _order in ("crawl_first", "crawl_last", "modified_date"):
            order_by = (sort, "title")
        elif _order in ("title", "url"):
            if q:
                order_by = (sort, "-rank")
            else:
                order_by = (sort,)

        data["order_by"] = order_by

        return data


class SearchResult(DocumentSerializer):
    score = serializers.SerializerMethodField(
        allow_null=True, help_text="Score of the document for provided search terms"
    )
    headline = serializers.SerializerMethodField(
        allow_null=True, help_text="Highlighted excerpt of the document content"
    )

    class Meta:
        model = Document
        fields = "__all__"

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret.pop("content")
        ret.pop("normalized_content")
        ret.pop("vector")
        return ret

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_score(self, obj):
        return getattr(obj, "rank", 1.0)

    @extend_schema_field(OpenApiTypes.STR)
    def get_headline(self, obj):
        return getattr(obj, "headline", "")


class SearchViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    @extend_schema(
        request=SearchQuerySerializer,
        description="Search queries",
        responses={
            200: SearchResult(many=True),
        },
    )
    def create(self, request, *args, **kwargs):
        query_serializer = SearchQuerySerializer(data=request.data, context={"request": request})
        query_serializer.is_valid(raise_exception=True)
        validated_data = query_serializer.validated_data

        # Get documents based on query parameters
        documents, search_query = self._get_documents(request, validated_data)

        # Apply show_on_homepage filter if requested
        if validated_data.get("show_on_homepage"):
            documents = documents.filter(show_on_homepage=True)

        # Apply robotstxt_rejected filter if requested
        if validated_data.get("robotstxt_rejected") is not None:
            documents = documents.filter(robotstxt_rejected=validated_data["robotstxt_rejected"])

        # Apply has_error filter if requested
        if validated_data.get("has_error") is not None:
            if validated_data["has_error"]:
                documents = documents.exclude(error="")
            else:
                documents = documents.filter(error="")

        page = self.paginate_queryset(documents)
        add_headlines(page, search_query)
        serializer = SearchResult(page, many=True)
        return self.get_paginated_response(serializer.data)

    def _get_documents(self, request, validated_data):
        """Get documents based on search parameters (adapted from
        se.search.get_documents)"""
        REQUIRED_KEYS = ("ft", "ff", "fo", "fv")

        results = Document.objects.w_content().annotate(rank=models.Value(1.0))

        # Handle full-text search query
        q = validated_data.get("query", "")
        q = remove_accent(q)
        search_query = None
        if q:
            lang = validated_data["lang"]

            search_query = SearchQuery(q, config=lang, search_type="websearch")
            all_results = (
                Document.objects.w_content()
                .filter(vector=search_query)
                .annotate(
                    rank=SearchRank(models.F("vector"), search_query),
                )
            )
            results = all_results.exclude(rank__lte=0.01)

            if results.count() == 0:
                results = all_results

        # Handle hidden documents
        include_hidden = validated_data.get("include_hidden", False)
        if not request.user.has_perm("se.document_change") or not include_hidden:
            results = results.exclude(hidden=True)

        # Apply global filters
        if settings.SOSSE_EXCLUDE_NOT_INDEXED:
            results = results.exclude(crawl_last__isnull=True)
        if settings.SOSSE_EXCLUDE_REDIRECT:
            results = results.filter(redirect_url__isnull=True)

        # Handle advanced filters
        params = validated_data.get("adv_params", [])
        for f in params:
            cont = True
            for k in REQUIRED_KEYS:
                if not f.get(k):
                    break
            else:
                cont = False
            if cont:
                continue

            ftype = f["ft"]
            field = f["ff"]
            operator = f["fo"]
            value = f["fv"]
            case = f.get("fc", False) and True

            if operator == "contain" and case:
                param = "__contains"
            elif operator == "contain" and not case:
                param = "__icontains"
            elif operator == "regexp" and case:
                param = "__regex"
            elif operator == "regexp" and not case:
                param = "__iregex"
            elif operator == "equal" and case:
                param = "__exact"
            elif operator == "equal" and not case:
                param = "__iexact"
            else:
                raise Exception(f"Unknown operation {operator}")

            if field not in list(dict(FILTER_FIELDS).keys()):
                fields = list(dict(FILTER_FIELDS).keys())
                raise Exception(f"Invalid FILTER_FIELDS {field} / {fields}")

            if field == "doc":
                content_param = {"content" + param: value}
                title_param = {"title" + param: value}
                url_param = {"url" + param: value}
                qf = models.Q(**content_param) | models.Q(**title_param) | models.Q(**url_param)
            elif field in ("lto_url", "lto_txt", "lby_url", "lby_txt"):
                field, rel_field = field.split("_")
                subfield = "doc_to" if field == "lto" else "doc_from"
                field = "links_to" if field == "lto" else "linked_from"
                if rel_field == "url":
                    key1 = f"{field}__{subfield}__url{param}"
                    key2 = f"{field}__extern_url{param}"
                    qf = models.Q(**{key1: value}) | models.Q(**{key2: value})
                else:
                    key = f"{field}__text{param}"
                    qf = models.Q(**{key: value})
            elif field == "tag":
                key = f"name{param}"
                _tags = Tag.objects.filter(**{key: value})
                tags = set()
                for tag in _tags:
                    tags |= set(Tag.get_tree(tag))
                qf = models.Q(tags__in=tags)
            else:
                qparams = {field + param: value}
                qf = models.Q(**qparams)

            if ftype == "exc":
                qf = ~qf
            elif ftype == "inc":
                pass
            else:
                raise Exception(f"Query type {operator} not supported")

            logger.debug(f"filter {ftype} {qf}")
            results = results.filter(qf)

        # Handle collection filter
        collection_id = validated_data.get("collection")
        if collection_id:
            collection = Collection.objects.get(id=collection_id)
            results = results.filter(collection=collection)

        # Handle sorting (order_by is calculated in serializer validation)
        order_by = validated_data["order_by"]

        # Ensure a deterministic order by adding a secondary sort on "id"
        if getattr(settings, "TEST_MODE", False):
            order_by = list(order_by) + ["id"]

        results = results.order_by(*order_by).distinct()

        return results, search_query
