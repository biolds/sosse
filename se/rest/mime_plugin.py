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

from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from ..mime_plugin import MimePlugin
from .permissions import DjangoModelPermissionsRW


class MimePluginSerializer(serializers.ModelSerializer):
    class Meta:
        model = MimePlugin
        fields = "__all__"
        read_only_fields = ("builtin",)


class MimePluginViewSet(viewsets.ModelViewSet):
    queryset = MimePlugin.objects.all()
    serializer_class = MimePluginSerializer
    permission_classes = [DjangoModelPermissionsRW]

    def perform_create(self, serializer):
        serializer.save(builtin=False)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.builtin:
            # For builtin handlers, only allow modification of 'enabled' field
            allowed_fields = {"enabled"}
            request_fields = set(request.data.keys())
            if not request_fields.issubset(allowed_fields):
                forbidden_fields = request_fields - allowed_fields
                forbidden_fields = ", ".join(forbidden_fields)
                raise PermissionDenied(
                    f"Cannot modify fields {forbidden_fields} for built-in MIME handlers. Only 'enabled' can be modified."
                )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.builtin:
            # For builtin handlers, only allow modification of 'enabled' field
            allowed_fields = {"enabled"}
            request_fields = set(request.data.keys())
            if not request_fields.issubset(allowed_fields):
                forbidden_fields = request_fields - allowed_fields
                forbidden_fields = ", ".join(forbidden_fields)
                raise PermissionDenied(
                    f"Cannot modify fields {forbidden_fields} for built-in MIME handlers. Only 'enabled' can be modified."
                )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.builtin:
            raise PermissionDenied("Cannot delete built-in MIME handlers")
        return super().destroy(request, *args, **kwargs)
