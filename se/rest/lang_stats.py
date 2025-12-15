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

from django.conf import settings
from django.db import models
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from ..document import Document
from .permissions import IsSuperUserOrStaff


class LangStatsSerializer(serializers.Serializer):
    doc_count = serializers.IntegerField(help_text="Document count")
    lang = serializers.CharField(help_text="Language")


class LangStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperUserOrStaff]

    @extend_schema(
        description="HDD analytics",
        responses={
            200: LangStatsSerializer(many=True),
        },
    )
    def list(self, request):
        langs = []
        indexed_langs = (
            Document.objects.wo_content()
            .exclude(lang_iso_639_1__isnull=True)
            .values("lang_iso_639_1")
            .annotate(count=models.Count("lang_iso_639_1"))
            .order_by("-count")
        )
        if indexed_langs:
            for lang in indexed_langs:
                lang_iso = lang["lang_iso_639_1"]
                lang_desc = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {})
                title = lang_iso.title()
                if lang_desc.get("flag"):
                    title = title + " " + lang_desc["flag"]
                langs.append({"lang": title, "doc_count": lang["count"]})
        return Response(langs)
