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

from ..cookie import Cookie
from .mixins import BulkActionMixin
from .permissions import DjangoModelPermissionsRW


class CookieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cookie
        fields = (
            "id",
            "domain",
            "domain_cc",
            "inc_subdomain",
            "name",
            "value",
            "path",
            "expires",
            "secure",
            "same_site",
            "http_only",
        )


class CookieSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get(self.search_param, "")
        if search_term.startswith("http://") or search_term.startswith("https://"):
            cookies = Cookie.get_from_url(search_term, queryset, expire=False)
            cookies = sorted(cookies, key=lambda x: x.name)
            return Cookie.objects.filter(id__in=[c.id for c in cookies])
        return super().filter_queryset(request, queryset, view)


class CookieViewSet(BulkActionMixin, viewsets.ModelViewSet):
    queryset = Cookie.objects.order_by("domain", "domain_cc", "path", "name")
    serializer_class = CookieSerializer
    permission_classes = [DjangoModelPermissionsRW]
    filter_backends = [CookieSearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["domain", "path"]
    filterset_fields = ["domain", "domain_cc", "path", "name", "expires", "value"]
    ordering_fields = ["domain", "domain_cc", "path", "name", "expires", "value"]
    ordering = ["domain", "domain_cc", "path", "name"]
