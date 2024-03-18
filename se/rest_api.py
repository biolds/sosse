# Copyright 2022-2024 Laurent Defert
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

from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_field, extend_schema_serializer, OpenApiExample, OpenApiTypes
from rest_framework import mixins, routers, serializers, viewsets
from rest_framework.settings import api_settings
from rest_framework.permissions import DjangoObjectPermissions

from .document import Document
from .forms import SearchForm, FILTER_FIELDS, SORT
from .models import CrawlerStats
from .search import get_documents


class CrawlerStatsSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = CrawlerStats


class CrawlerStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CrawlerStats.objects.all()
    serializer_class = CrawlerStatsSerializer
    filterset_fields = ('freq',)
    permission_classes = [DjangoObjectPermissions]


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer


class SearchAdvancedQuery(serializers.Serializer):
    field = serializers.ChoiceField(choices=FILTER_FIELDS, default='doc', help_text='Field to filter on')
    type = serializers.ChoiceField(choices=(('inc', 'Include'), ('exc', 'Exclude')), default='inc', help_text='Type of filter')
    OP_CHOICES = ('contain', 'regexp', 'equal')
    operator = serializers.ChoiceField(choices=list(zip(OP_CHOICES, OP_CHOICES)), default='contain', help_text='Filtering operator')
    case_sensitive = serializers.BooleanField(default=False)
    term = serializers.CharField(help_text='Filtering terms')

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return {
            'ft': data['type'],
            'ff': data['field'],
            'fo': data['operator'],
            'fv': data['term'],
            'fc': data['case_sensitive']
        }


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Simple search query',
            value={
                'query': 'big cats',
            }
        ),
        OpenApiExample(
            'Advanced search query',
            value={
                'query': 'big cats',
                'adv_params': [{
                    'field': 'url',
                    'term': 'https://wikipedia.org/',
                }]
            }
        )
    ]
)
class SearchQuery(serializers.Serializer):
    query = serializers.CharField(default='', allow_blank=True, help_text='Search terms')
    lang = serializers.ChoiceField(default='en', choices=[(key, val['name'].title()) for key, val in settings.SOSSE_LANGDETECT_TO_POSTGRES.items()], help_text='Search terms language')
    sort = serializers.ChoiceField(default='-rank', choices=SORT, help_text='Results sorting')
    adv_params = SearchAdvancedQuery(many=True, default=[], help_text='Advanced search parameters')

    def validate(self, data):
        data = super().validate(data)
        if not data.get('adv_params') and not data.get('query'):
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: 'At least "query" or "adv_params" field must be provided.'})
        return data


class SearchResult(serializers.Serializer):
    doc_id = serializers.PrimaryKeyRelatedField(source='id', queryset=Document.objects.all(), help_text='Document id')
    url = serializers.CharField(help_text='Document URL')
    title = serializers.CharField(help_text='Document Title')
    score = serializers.SerializerMethodField(allow_null=True, help_text='Score of the document for provided search terms')

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_score(self, obj):
        return getattr(obj, 'rank', None)


class SearchViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    @extend_schema(
        request=SearchQuery,
        description='Search queries',
        responses={
            200: SearchResult(many=True),
        }
    )
    def create(self, request, *args, **kwargs):
        query = SearchQuery(data=request.data)
        query.is_valid(raise_exception=True)
        f = SearchForm(data={
            'q': query.validated_data['query'],
            'l': query.validated_data['lang'],
            's': query.validated_data['sort']
        })
        f.is_valid()
        _, documents, _ = get_documents(query.validated_data['adv_params'], f, False)
        page = self.paginate_queryset(documents)
        serializer = SearchResult(page, many=True)
        return self.get_paginated_response(serializer.data)


router = routers.DefaultRouter()
router.register('document', DocumentViewSet)
router.register('search', SearchViewSet, basename='search')
router.register('stats', CrawlerStatsViewSet)
