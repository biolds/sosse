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

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class UserProfileSerializer(serializers.Serializer):
    """Serializer for user profile."""

    username = serializers.CharField()
    is_authenticated = serializers.BooleanField(default=True)
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()


class ProfileViewSet(viewsets.ViewSet):
    """ViewSet for current user profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        description="Returns the username and authentication status of the currently authenticated user.",
        responses={
            200: UserProfileSerializer(),
        },
    )
    def list(self, request):
        """Return current user profile."""
        serializer = UserProfileSerializer(
            {
                "username": request.user.username,
                "is_authenticated": True,
                "is_staff": request.user.is_staff,
                "is_superuser": request.user.is_superuser,
            }
        )
        return Response(serializer.data)
