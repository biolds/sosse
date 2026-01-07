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

from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response


class BulkActionSerializer(serializers.Serializer):
    action = serializers.CharField(required=True)
    ids = serializers.ListField(child=serializers.IntegerField(), required=True)


class BulkActionMixin:
    @action(detail=False, methods=["post"])
    def action(self, request):
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data["action"]
        ids = serializer.validated_data["ids"]

        if action_name == "delete":
            queryset = self.get_queryset().filter(id__in=ids)
            count = queryset.count()
            queryset.delete()
            return Response(
                {"deleted": count},
                status=status.HTTP_200_OK,
            )

        action_method_name = f"bulk_{action_name}"
        if not hasattr(self, action_method_name):
            return Response(
                {"error": f"action '{action_name}' not supported"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        method = getattr(self, action_method_name)
        if not callable(method):
            return Response(
                {"error": f"'{action_name}' is not callable"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        errors = []
        queryset = self.get_queryset().filter(id__in=ids)

        for obj in queryset:
            try:
                result = method(obj, request)
                results.append({"id": obj.id, "result": result})
            except Exception as e:
                errors.append({"id": obj.id, "error": str(e)})

        return Response(
            {"results": results, "errors": errors},
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )

    def get_serializer_class(self):
        if self.request.query_params.get("ids_only") == "1":
            _model = self.get_queryset().model

            class IdsOnlySerializer(serializers.ModelSerializer):
                class Meta:
                    model = _model
                    fields = ("id",)

            return IdsOnlySerializer
        return super().get_serializer_class()
