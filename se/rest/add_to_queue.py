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

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiTypes,
    extend_schema,
    extend_schema_serializer,
)
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from ..add_to_queue import AddToQueueForm, queue_urls
from ..collection import Collection
from ..document import Document
from ..models import WorkerStats
from ..url import sanitize_url, validate_url
from .permissions import DjangoModelPermissionsRW


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Simple URLs queue",
            value={
                "urls": ["http://example.com", "https://test.com/page"],
                "collection": 1,
            },
        ),
        OpenApiExample(
            "URLs with crawl scope",
            value={
                "urls": ["http://example.com"],
                "collection": 1,
                "crawl_scope": "unlimited",
                "show_on_homepage": True,
            },
        ),
    ]
)
class AddToQueueSerializer(serializers.Serializer):
    urls = serializers.ListField(child=serializers.URLField(), help_text="URLs to queue for crawling")
    collection = serializers.PrimaryKeyRelatedField(
        queryset=Collection.objects.all(), help_text="Collection to crawl with"
    )
    crawl_scope = serializers.ChoiceField(
        choices=AddToQueueForm.CRAWL_SCOPE_CHOICES,
        default=AddToQueueForm.CRAWL_SCOPE_NO_CHANGE,
        help_text="How to crawl the websites from these URLs",
    )
    show_on_homepage = serializers.BooleanField(default=True, help_text="Display the initial document on the homepage")

    def validate_urls(self, value):
        validated_urls = []
        errors = []

        for i, url in enumerate(value):
            try:
                sanitized_url = sanitize_url(url)
                validate_url(sanitized_url)
                validated_urls.append(sanitized_url)
            except Exception as e:
                errors.append(f"URL {i + 1}: {str(e)}")

        if errors:
            raise serializers.ValidationError(errors)

        return validated_urls


class AddToQueueViewSet(viewsets.ViewSet):
    serializer_class = AddToQueueSerializer
    permission_classes = [DjangoModelPermissionsRW]
    queryset = Document.objects.wo_content()

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    @extend_schema(
        request=AddToQueueSerializer,
        description="Add URLs to crawl queue",
        responses={
            201: OpenApiTypes.OBJECT,
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        urls = serializer.validated_data["urls"]
        collection = serializer.validated_data["collection"]
        crawl_scope = serializer.validated_data["crawl_scope"]
        show_on_homepage = serializer.validated_data["show_on_homepage"]

        # Use the shared function from add_to_queue.py
        queue_urls(urls, collection, show_on_homepage, crawl_scope)
        WorkerStats.wake_up()

        url_count = len(urls)
        message = f"{url_count} URL{'s' if url_count > 1 else ''} queued successfully"

        return Response(
            {
                "message": message,
                "queued_urls": urls,
                "collection": collection.id,
                "crawl_scope": crawl_scope,
                "show_on_homepage": show_on_homepage,
            },
            status=201,
        )
