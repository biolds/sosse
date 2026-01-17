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

from django.db.models import Count, Max, Min, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter

from ..collection import Collection
from ..tag import Tag
from ..webhook import Webhook
from .permissions import DjangoModelPermissionsRW


class CollectionSerializer(serializers.ModelSerializer):
    webhooks = serializers.PrimaryKeyRelatedField(many=True, queryset=Webhook.objects.all(), required=False)
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)
    documents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Collection
        fields = "__all__"
        read_only_fields = (
            "unlimited_regex_pg",
            "limited_regex_pg",
            "excluded_regex_pg",
        )


class CollectionDetailSerializer(CollectionSerializer):
    robotstxt_rejected = serializers.IntegerField(read_only=True)
    crawl_first = serializers.DateTimeField(read_only=True)
    crawl_last = serializers.DateTimeField(read_only=True)
    crawl_next = serializers.DateTimeField(read_only=True)
    errors = serializers.IntegerField(read_only=True)


class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [DjangoModelPermissionsRW]
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    ordering_fields = ["name", "documents_count"]
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CollectionDetailSerializer
        return CollectionSerializer

    @extend_schema(responses=CollectionDetailSerializer)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Collection.objects.annotate(documents_count=Count("document"))

        if self.action == "retrieve":
            queryset = queryset.annotate(
                robotstxt_rejected=Count("document", filter=Q(document__robotstxt_rejected=True)),
                crawl_first=Min("document__crawl_first"),
                crawl_last=Max("document__crawl_last"),
                crawl_next=Min("document__crawl_next"),
                errors=Count("document", filter=~Q(document__error="")),
            )

        return queryset
