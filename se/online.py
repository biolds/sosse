# Copyright 2022-2025 Laurent Defert
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

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import View

from .browser_request import BrowserRequest
from .login import LoginRequiredMixin
from .search_form import SearchForm

check_cache_count = 0
check_cache_value = None


def online_status(request):
    if not settings.SOSSE_ONLINE_SEARCH_REDIRECT:
        return ""

    form = SearchForm(request.GET)
    if form.is_valid():
        if form.cleaned_data["o"] == "o":
            return "online"
        elif form.cleaned_data["o"] == "l":
            return "offline"

    global check_cache_count, check_cache_value
    try:
        if settings.SOSSE_ONLINE_CHECK_CACHE is None and check_cache_value:
            return check_cache_value

        if check_cache_count != 0:
            check_cache_count -= 1
            if check_cache_value:
                return check_cache_value

        check_cache_count = settings.SOSSE_ONLINE_CHECK_CACHE
        BrowserRequest.get(
            settings.SOSSE_ONLINE_CHECK_URL,
            timeout=settings.SOSSE_ONLINE_CHECK_TIMEOUT,
            check_status=True,
        )
        check_cache_value = "online"
    except requests.exceptions.RequestException:
        check_cache_value = "offline"
    return check_cache_value


class OnlineCheckView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            BrowserRequest.get(settings.SOSSE_ONLINE_CHECK_URL, check_status=True)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"status": e.__doc__, "success": False})

        return JsonResponse({"status": "Success", "success": True})
