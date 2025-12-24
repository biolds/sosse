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

import re

from django.conf import settings
from rest_framework import serializers, viewsets
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from ..document import Document
from ..models import Link
from .permissions import DjangoModelPermissionsRW


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = ("id", "text", "pos", "link_no", "extern_url", "screen_pos", "in_nav")


class ScreenshotSerializer(serializers.Serializer):
    screenshot = serializers.CharField()
    links = LinkSerializer(many=True)


class ScreenshotViewSet(viewsets.ViewSet):
    permission_classes = [DjangoModelPermissionsRW]

    def get_queryset(self):
        return Document.objects.w_content()

    def get_object(self):
        url = self.request.META["REQUEST_URI"].split("/", 3)[-1]
        if re.match(r"[0-9]+/?$", url):
            url = url.rstrip("/")
            instance = Document.objects.w_content().filter(pk=url).first()
        else:
            url = self.request.META["REQUEST_URI"].split("/", 3)[-1]
            instance = Document.objects.w_content().filter(url=url).first()
        return instance

    def retrieve(self, request, pk=None):
        doc = self.get_object()
        if not doc:
            return Response({"error": "Document not found"}, status=404)

        if not doc.screenshot_count:
            return Response({"error": "No screenshot available"}, status=404)

        # Get links with screen position
        links = list(doc.links_to.filter(screen_pos__isnull=False).order_by("link_no"))
        for link in links:
            if link.doc_to:
                continue
            link.extern_url = request.build_absolute_uri("/html/" + link.extern_url)

        data = {
            "screenshot": settings.SOSSE_SCREENSHOTS_URL + "/" + doc.image_name(),
            "links": links,
        }

        serializer = ScreenshotSerializer(data)
        return Response(serializer.data)

    def list(self, request):
        raise MethodNotAllowed("GET")

    def create(self, request):
        raise MethodNotAllowed("POST")

    def update(self, request, pk=None):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, pk=None):
        raise MethodNotAllowed("PATCH")

    def destroy(self, request, pk=None):
        raise MethodNotAllowed("DELETE")
