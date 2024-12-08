# Copyright 2024 Laurent Defert
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

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import RequestFactory
from django.test.client import Client


class ViewsTestMixin:
    def setUp(self):
        super().setUp()
        self.user = User.objects.create(username='admin', is_superuser=True, is_staff=True)
        self.user.set_password('admin')
        self.user.save()

        self.factory = RequestFactory()
        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self.assertTrue(self.client.login(username='admin', password='admin'))

    def _request_from_factory(self, url: str, user: User | None = None) -> HttpRequest:
        request = self.factory.get(url)
        request.META['REQUEST_URI'] = url
        request.META['REQUEST_SCHEME'] = 'http'
        request.META['HTTP_HOST'] = '127.0.0.1'
        request.user = user or self.user
        return request
