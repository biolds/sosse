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
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from ..document import Document
from ..models import WorkerStats
from ..utils import human_dt
from .permissions import IsSuperUserOrStaff


class CrawlQueueDocumentSerializer(serializers.ModelSerializer):
    crawl_next_human = serializers.SerializerMethodField()
    crawl_last_human = serializers.SerializerMethodField()
    title = serializers.CharField(read_only=True)
    favicon_url = serializers.SerializerMethodField()
    is_pending = serializers.SerializerMethodField()
    in_history = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "url",
            "title",
            "favicon_url",
            "crawl_next",
            "crawl_next_human",
            "crawl_last",
            "crawl_last_human",
            "retries",
            "worker_no",
            "is_pending",
            "in_history",
        ]

    def get_crawl_next_human(self, obj):
        if obj.crawl_next:
            return human_dt(obj.crawl_next, True)
        return None

    def get_crawl_last_human(self, obj):
        if obj.crawl_last:
            return human_dt(obj.crawl_last, True)
        return None

    def get_favicon_url(self, obj):
        if obj.favicon and not obj.favicon.missing:
            return f"/favicon/{obj.favicon.id}"
        return None

    def get_is_pending(self, obj):
        return getattr(obj, "pending", False)

    def get_in_history(self, obj):
        return getattr(obj, "in_history", False)


class CrawlQueueActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["pause", "resume"], required=True)


class CrawlQueueViewSet(APIView):
    permission_classes = [IsSuperUserOrStaff]

    def get(self, request):
        total_documents = Document.objects.w_content().count()
        queue_new_count = Document.objects.wo_content().filter(crawl_last__isnull=True).count()
        queue_recurring_count = (
            Document.objects.wo_content().filter(crawl_last__isnull=False, crawl_next__isnull=False).count()
        )
        queue_pending_count = (
            Document.objects.wo_content()
            .filter(models.Q(crawl_last__isnull=True) | models.Q(crawl_next__lte=now()))
            .count()
        )

        queue = Document.crawl_queue(True)
        serializer = CrawlQueueDocumentSerializer(queue, many=True)

        return Response(
            {
                "pause": WorkerStats.objects.filter(state="paused").count() == 0,
                "queue": serializer.data,
                "total_documents": total_documents,
                "queue_new_count": queue_new_count,
                "queue_recurring_count": queue_recurring_count,
                "queue_pending_count": queue_pending_count,
                "now": now(),
            }
        )

    def post(self, request):
        serializer = CrawlQueueActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        if action == "pause":
            WorkerStats.objects.update(state="paused")
        elif action == "resume":
            WorkerStats.objects.update(state="running")
            WorkerStats.wake_up()
        return self.get(request)
