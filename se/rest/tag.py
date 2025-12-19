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

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..tag import Tag
from .permissions import DjangoModelPermissionsRW


class TagSerializer(serializers.ModelSerializer):
    color = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = "__all__"

    def get_color(self, obj):
        return obj.get_color()


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permissions = [DjangoModelPermissionsRW]

    @action(detail=False)
    def tree_doc_counts(self, request):
        return Response(Tag.tree_doc_counts())
