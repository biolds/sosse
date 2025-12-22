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

from django.conf import settings
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
from ..document import Document
from ..search import add_headlines, get_documents
from ..search_form import FILTER_FIELDS, SORT, SearchForm
from .document import DocumentSerializer


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
    collection = serializers.IntegerField(required=False, help_text="Filter by collection ID")
    adv_params = SearchAdvancedQuery(many=True, default=[], help_text="Advanced search parameters")
    show_on_homepage = serializers.BooleanField(
        default=False,
        help_text="Filter documents shown on homepage",
    )

    def validate(self, data):
        data = super().validate(data)
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
                "collection": query.validated_data.get("collection", ""),
            }
        )
        f.is_valid()
        _, documents, search_query = get_documents(request, query.validated_data["adv_params"], f, False)

        # Apply show_on_homepage filter if requested
        if query.validated_data.get("show_on_homepage"):
            documents = documents.filter(show_on_homepage=True)

        page = self.paginate_queryset(documents)
        add_headlines(page, search_query)
        serializer = SearchResult(page, many=True)
        return self.get_paginated_response(serializer.data)
