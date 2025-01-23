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

from typing import Type

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template.response import SimpleTemplateResponse
from django.test import RequestFactory
from django.test.client import Client
from django.views.generic import View


class ViewsTestMixin:
    def setUp(self):
        super().setUp()
        messages.success = lambda request, message: None

        self.admin_user = User.objects.create(username="admin", is_superuser=True, is_staff=True)
        self.admin_user.set_password("admin")
        self.admin_user.save()
        self.staff_user = User.objects.create(username="staff", is_staff=True)
        self.staff_user.set_password("staff")
        self.staff_user.save()
        self.simple_user = User.objects.create(username="user")
        self.simple_user.set_password("user")
        self.simple_user.save()
        self.anon_user = AnonymousUser()

        self.factory = RequestFactory()
        self.admin_client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.assertTrue(self.admin_client.login(username="admin", password="admin"))

        self.staff_client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.assertTrue(self.staff_client.login(username="staff", password="staff"))

        self.simple_client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.assertTrue(self.simple_client.login(username="user", password="user"))

        self.anon_client = Client(HTTP_USER_AGENT="Mozilla/5.0")

    def _request_from_factory(
        self, url: str, user: User, method: str = "get", params: dict | None = None
    ) -> HttpRequest:
        params = params or {}
        request = getattr(self.factory, method)(url, params)
        request.META["REQUEST_URI"] = url
        request.META["REQUEST_SCHEME"] = "http"
        request.META["HTTP_HOST"] = "127.0.0.1"
        request.user = user
        return request

    def _view_request(self, url: str, view_cls: Type[View], params: dict, user: User, expected_status: int):
        view = view_cls.as_view()
        request = self._request_from_factory(url, user)
        try:
            response = view(request, **params)
            if isinstance(response, SimpleTemplateResponse):
                response.render()
        except PermissionDenied:
            response = HttpResponse(content="Permission denied", status=403)
        except:  # noqa
            raise Exception(f"Failed on {url}")
        self.assertEqual(
            response.status_code,
            expected_status,
            f"{url}\n{response.status_code} != {expected_status}\n{user}\n{response.content}\n{response.headers}",
        )
        return response
