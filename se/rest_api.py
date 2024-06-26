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

import os

from django.db import connection, models
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_field, extend_schema_serializer, OpenApiExample, OpenApiTypes
from rest_framework import mixins, routers, serializers, viewsets
from rest_framework.settings import api_settings
from rest_framework.response import Response


from .document import Document
from .forms import SearchForm, FILTER_FIELDS, SORT
from .models import CrawlerStats
from .rest_permissions import IsSuperUserOrStaff
from .search import get_documents


class CrawlerStatsSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = CrawlerStats


class CrawlerStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CrawlerStats.objects.order_by('t')
    serializer_class = CrawlerStatsSerializer
    filterset_fields = ('freq',)
    permission_classes = [IsSuperUserOrStaff]


class HddStatsSerializer(serializers.Serializer):
    db = serializers.IntegerField(help_text='Size of the database')
    screenshots = serializers.IntegerField(help_text='Size of the screenshots')
    html = serializers.IntegerField(help_text='Size of HTML dumps')
    other = serializers.IntegerField(help_text='Data not used by SOSSE')
    free = serializers.IntegerField(help_text='Free space')


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
        description='HDD statistics',
        responses={
            200: HddStatsSerializer(),
        }
    )
    def list(self, request):
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_database_size(%s)', [settings.DATABASES['default']['NAME']])
            db_size = cursor.fetchall()[0][0]

        statvfs = os.statvfs('/var/lib')
        hdd_size = statvfs.f_frsize * statvfs.f_blocks
        hdd_free = statvfs.f_frsize * statvfs.f_bavail

        screenshot_size = self.dir_size(settings.SOSSE_SCREENSHOTS_DIR)
        html_size = self.dir_size(settings.SOSSE_HTML_SNAPSHOT_DIR)
        hdd_other = hdd_size - hdd_free - db_size - screenshot_size - html_size
        return Response({
            'db': db_size,
            'screenshots': screenshot_size,
            'html': html_size,
            'other': hdd_other,
            'free': hdd_free
        })


class LangStatsSerializer(serializers.Serializer):
    doc_count = serializers.IntegerField(help_text='Document count')
    lang = serializers.CharField(help_text='Language')


class LangStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    @extend_schema(
        description='HDD statistics',
        responses={
            200: LangStatsSerializer(many=True),
        }
    )
    def list(self, request):
        langs = []
        indexed_langs = Document.objects.exclude(lang_iso_639_1__isnull=True).values('lang_iso_639_1').annotate(count=models.Count('lang_iso_639_1')).order_by('-count')
        if indexed_langs:
            for lang in indexed_langs:
                lang_iso = lang['lang_iso_639_1']
                lang_desc = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {})
                title = lang_iso.title()
                if lang_desc.get('flag'):
                    title = title + ' ' + lang_desc['flag']
                langs.append({
                    'lang': title,
                    'doc_count': lang['count']
                })
        return Response(langs)


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
    include_hidden = serializers.BooleanField(default=False, help_text='Include hidden documents, requires the permission "Can change documents"')
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
        # ×raise Exception(query.validated_data)
        f = SearchForm(data={
            'q': query.validated_data['query'],
            'l': query.validated_data['lang'],
            's': query.validated_data['sort'],
            'i': 'on' if query.validated_data['include_hidden'] else ''
        })
        f.is_valid()
        _, documents, _ = get_documents(request, query.validated_data['adv_params'], f, False)
        page = self.paginate_queryset(documents)
        serializer = SearchResult(page, many=True)
        return self.get_paginated_response(serializer.data)


router = routers.DefaultRouter()
router.register('document', DocumentViewSet)
router.register('search', SearchViewSet, basename='search')
router.register('stats', CrawlerStatsViewSet)
router.register('hdd_stats', HddStatsViewSet, basename='hdd_stats')
router.register('lang_stats', LangStatsViewSet, basename='lang_stats')
