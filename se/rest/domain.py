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

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from ..domain import Domain
from .mixins import BulkActionMixin
from .permissions import DjangoModelPermissionsRW


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = (
            "id",
            "domain",
            "browse_mode",
            "robots_status",
            "robots_ua_hash",
            "robots_allow",
            "robots_disallow",
            "ignore_robots",
        )


class DomainViewSet(BulkActionMixin, viewsets.ModelViewSet):
    queryset = Domain.objects.order_by("domain")
    serializer_class = DomainSerializer
    permission_classes = [DjangoModelPermissionsRW]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["domain"]
    filterset_fields = ["domain", "browse_mode", "robots_status", "ignore_robots"]
    ordering_fields = ["domain", "browse_mode", "robots_status", "ignore_robots"]
    ordering = ["domain"]
