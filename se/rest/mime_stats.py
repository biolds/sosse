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


from django.db import models
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from ..document import Document
from ..utils import mimetype_icon
from .permissions import IsSuperUserOrStaff


class MimeStatsSerializer(serializers.Serializer):
    doc_count = serializers.IntegerField(help_text="Document count")
    mime = serializers.CharField(help_text="Mimetype")


class MimeStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    @extend_schema(
        description="Mimetype analytics",
        responses={
            200: MimeStatsSerializer(many=True),
        },
    )
    def list(self, request):
        indexed_mimes = (
            Document.objects.wo_content()
            .annotate(
                mimetype_coalesced=Coalesce("mimetype", models.Value("NULL"))
            )  # Coalesce otherwise PG does not count NULL values
            .values("mimetype_coalesced")
            .annotate(doc_count=models.Count("*"))
            .order_by("-doc_count", "mimetype")
        )

        indexed_mimes = {a["mimetype_coalesced"]: a["doc_count"] for a in indexed_mimes}
        null_count = indexed_mimes.pop("NULL", 0)

        if null_count:
            indexed_mimes[""] = indexed_mimes.get("", 0) + null_count

        indexed_mimes = sorted(
            [{"mimetype": mime, "doc_count": count} for mime, count in indexed_mimes.items()],
            key=lambda x: -x["doc_count"],
        )

        for indexed_mime in indexed_mimes:
            mimetype = indexed_mime["mimetype"]
            icon = mimetype_icon(mimetype)
            if mimetype:
                indexed_mime["mimetype"] = f"{icon} {mimetype}"
            else:
                indexed_mime["mimetype"] = f"{icon} <None>"

        return Response(indexed_mimes)
