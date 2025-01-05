# Copyright 2025 Laurent Defert
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

from django.shortcuts import redirect, reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .login import login_required


@method_decorator(login_required, name="dispatch")
class StatisticsView(TemplateView):
    template_name = "admin/stats.html"
    extra_context = {"title": "Statistics"}

    def get(self, request):
        if not request.user.is_staff or not request.user.is_superuser:
            return redirect(reverse("search"))
        return super().get(request)
