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
from drf_spectacular.utils import (
    OpenApiTypes,
    extend_schema_field,
)
from rest_framework import serializers, viewsets
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.validators import ValidationError

from ..browser import SkipIndexing
from ..document import Document
from ..favicon import FavIcon
from ..html_asset import HTMLAsset
from ..tag import Tag
from .permissions import DjangoModelPermissionsRW


class TagSlugRelatedField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        if isinstance(data, int):
            return Tag.objects.get(pk=data)

        tag, _ = Tag.objects.get_or_create(name=data)
        return tag


class FavIconSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavIcon
        fields = ("id", "missing")


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = "__all__"
        read_only_fields = (
            "url",
            "normalized_content",
            "normalized_url",
            "normalized_title",
            "content_hash",
            "favicon",
            "robotstxt_rejected",
            "has_html_snapshot",
            "redirect_url",
            "too_many_redirects",
            "screenshot_count",
            "screenshot_format",
            "screenshot_size",
            "has_thumbnail",
            "crawl_first",
            "crawl_last",
            "crawl_next",
            "crawl_dt",
            "crawl_recurse",
            "modified_date",
            "manual_crawl",
            "error",
            "error_hash",
            "worker_no",
        )

    tags = TagSlugRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field="name",
    )

    favicon = FavIconSerializer(read_only=True)
    tags_str = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    snapshot_url = serializers.SerializerMethodField()

    def get_tags_str(self, obj):
        if obj.id:
            # Accessing obj.tags thru many-to-many relation requires the object to exist
            return ", ".join([tag.name for tag in obj.tags.order_by("name")])
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_preview(self, obj):
        if obj.has_thumbnail:
            return f"{settings.SOSSE_THUMBNAILS_URL}{obj.image_name()}.jpg"
        elif obj.screenshot_count:
            return f"{settings.SOSSE_SCREENSHOTS_URL}{obj.image_name()}_0.{obj.screenshot_format}"
        elif obj.mimetype and obj.mimetype.startswith("image/") and obj.has_html_snapshot:
            asset = HTMLAsset.objects.filter(url=obj.url).first()
            if asset:
                return settings.SOSSE_HTML_SNAPSHOT_URL + asset.filename
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_snapshot_url(self, obj):
        if obj.has_html_snapshot:
            asset = HTMLAsset.objects.filter(url=obj.url).first()
            if asset:
                return settings.SOSSE_HTML_SNAPSHOT_URL + asset.filename
        return None

    def user_doc_update(self, ctx_msg):
        try:
            self.is_valid(raise_exception=True)
            self.update(self.instance, self.validated_data)
        except ValidationError as e:
            raise SkipIndexing(f"{ctx_msg} result validation error:\n{e.detail}\nInput data was:\n{self.data}\n---")
        except Exception as e:
            msg = f"{ctx_msg} document update error:\n{e.args[0]}\nInput data was:\n{self.data}\n---"
            e.args = (msg,) + e.args[1:]
            raise e

    def validate(self, attrs):
        attrs = super().validate(attrs)
        title = attrs.get("title")
        if title is not None:
            attrs["normalized_title"] = Document._normalized_title(title)
        content = attrs.get("content")
        if content is not None:
            attrs["normalized_content"] = Document._normalized_content(content)
        return attrs


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.w_content()
    serializer_class = DocumentSerializer
    permission_classes = [DjangoModelPermissionsRW]
    lookup_field = "pk"

    def get_object(self):
        url = self.request.META["REQUEST_URI"].split("/", 3)[-1]
        if re.match(r"[0-9]+/?$", url):
            url = url.rstrip("/")
            instance = Document.objects.w_content().filter(pk=url).first()
        else:
            url = self.request.META["REQUEST_URI"].split("/", 3)[-1]
            instance = Document.objects.w_content().filter(url=url).first()
        return instance

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")
