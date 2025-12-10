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
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"  # nosec B105


class CookieTokenObtainPairView(TokenObtainPairView):
    """JWT token obtain view that stores refresh token in HttpOnly cookie."""

    def finalize_response(self, request, response, *args, **kwargs):
        if response.status_code == status.HTTP_200_OK and "refresh" in response.data:
            refresh_token = response.data.pop("refresh")
            response.set_cookie(
                key=REFRESH_TOKEN_COOKIE_NAME,
                value=refresh_token,
                httponly=True,
                secure=settings.SOSSE_SECURE_COOKIE,
                samesite="Strict",
                max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
            )
        return super().finalize_response(request, response, *args, **kwargs)


class CookieTokenRefreshView(TokenRefreshView):
    """JWT token refresh view that reads refresh token from HttpOnly cookie."""

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)
        if refresh_token:
            request.data["refresh"] = refresh_token
        return super().post(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        if response.status_code == status.HTTP_200_OK and "refresh" in response.data:
            refresh_token = response.data.pop("refresh")
            response.set_cookie(
                key=REFRESH_TOKEN_COOKIE_NAME,
                value=refresh_token,
                httponly=True,
                secure=settings.SOSSE_SECURE_COOKIE,
                samesite="Strict",
                max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
            )
        return super().finalize_response(request, response, *args, **kwargs)


class CookieTokenLogoutView(TokenRefreshView):
    """JWT logout view that deletes the refresh token cookie."""

    def post(self, request, *args, **kwargs):
        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            samesite="Strict",
        )
        return response
