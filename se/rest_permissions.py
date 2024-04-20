# Copyright 2022-2024 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

from django.conf import settings
from rest_framework import permissions


class LoginRequiredPermission(permissions.BasePermission):
    def has_permission(self, request, _):
        if settings.SOSSE_ANONYMOUS_SEARCH:
            return True
        return request.user.is_authenticated


class IsSuperUserOrStaff(permissions.BasePermission):
    def has_permission(self, request, _):
        return request.user and (request.user.is_superuser or request.user.is_staff)
