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

from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
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


class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [DjangoModelPermissionsRW]
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    ordering_fields = ["name", "documents_count"]
    search_fields = ["name"]

    def get_queryset(self):
        return Collection.objects.annotate(documents_count=Count("document"))
