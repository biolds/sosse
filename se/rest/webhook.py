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

import logging

from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.validators import ValidationError

from ..document import example_doc
from ..webhook import Webhook, webhook_html_status
from .permissions import DjangoModelPermissionsRW

webhook_logger = logging.getLogger("webhooks")


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = "__all__"


class WebhookTestTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        exclude = ("name",)


class WebhookViewSet(viewsets.ModelViewSet):
    queryset = Webhook.objects.all()
    serializer_class = WebhookSerializer
    permissions = [DjangoModelPermissionsRW]

    @action(detail=False, methods=["post"])
    def test_trigger(self, request):
        as_html = request.GET.get("as_html")
        serializer = WebhookTestTriggerSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            webhook = Webhook(**serializer.validated_data)
            result = webhook.send(example_doc())
        except ValueError as e:
            webhook_logger.exception("Webhook error")
            if not as_html:
                return Response({"error": str(e)}, status=400)
            result = {"error": str(e)}
        except ValidationError as e:
            result = {"error": f"Webhook configuration error:\n{e.detail}"}

        if request.GET.get("as_html"):
            return HttpResponse(webhook_html_status(result))
        return Response(result)
