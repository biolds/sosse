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


from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LoginView


class SosseLoginRequiredMixin(UserPassesTestMixin):
    login_url = None
    redirect_field_name = REDIRECT_FIELD_NAME

    def test_func(self):
        if settings.SOSSE_ANONYMOUS_SEARCH:
            return True
        return self.request.user.is_authenticated


class SELoginView(LoginView):
    template_name = "admin/login.html"
