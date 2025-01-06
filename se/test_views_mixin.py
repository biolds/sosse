# Copyright 2024-2025 Laurent Defert
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

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest
from django.test import RequestFactory
from django.test.client import Client


class ViewsTestMixin:
    def setUp(self):
        super().setUp()
        self.admin_user = User.objects.create(username="admin", is_superuser=True, is_staff=True)
        self.admin_user.set_password("admin")
        self.admin_user.save()
        self.simple_user = User.objects.create(username="user")
        self.simple_user.set_password("user")
        self.simple_user.save()
        self.anon_user = AnonymousUser()

        self.factory = RequestFactory()
        self.admin_client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.assertTrue(self.admin_client.login(username="admin", password="admin"))

        self.simple_client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.assertTrue(self.simple_client.login(username="user", password="user"))

        self.anon_client = Client(HTTP_USER_AGENT="Mozilla/5.0")

    def _request_from_factory(self, url: str, user: User) -> HttpRequest:
        request = self.factory.get(url)
        request.META["REQUEST_URI"] = url
        request.META["REQUEST_SCHEME"] = "http"
        request.META["HTTP_HOST"] = "127.0.0.1"
        request.user = user
        return request
