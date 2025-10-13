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

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import View

from .browser_request import BrowserRequest
from .login import SosseLoginRequiredMixin
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
            None,
            timeout=settings.SOSSE_ONLINE_CHECK_TIMEOUT,
            check_status=True,
        )
        check_cache_value = "online"
    except requests.exceptions.RequestException:
        check_cache_value = "offline"
    return check_cache_value


class OnlineCheckView(SosseLoginRequiredMixin, View):
    def get(self, request):
        try:
            BrowserRequest.get(settings.SOSSE_ONLINE_CHECK_URL, None, check_status=True)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"status": e.__doc__, "success": False})

        return JsonResponse({"status": "Success", "success": True})
