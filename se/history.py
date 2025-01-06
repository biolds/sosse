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

from django.conf import settings
from django.core.paginator import Paginator

from .models import SearchHistory
from .views import UserView


class HistoryView(UserView):
    template_name = "se/history.html"
    title = "History"

    def test_func(self):
        # Require authentication whatever the value of SOSSE_ANONYMOUS_SEARCH
        return self.request.user.is_authenticated

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_size = int(self.request.GET.get("ps", settings.SOSSE_DEFAULT_PAGE_SIZE))
        page_size = min(page_size, settings.SOSSE_MAX_PAGE_SIZE)

        history = SearchHistory.objects.filter(user=self.request.user).order_by("-date")
        paginator = Paginator(history, page_size)
        page_number = int(self.request.GET.get("p", 1))
        paginated = paginator.get_page(page_number)

        context["paginated"] = paginated
        context.update(self._get_pagination(paginated))
        return context

    def post(self, request):
        if "del_all" in self.request.POST:
            SearchHistory.objects.filter(user=self.request.user).delete()
        else:
            for key, val in self.request.POST.items():
                if key.startswith("del_"):
                    key = int(key[4:])
                    obj = SearchHistory.objects.filter(id=key, user=self.request.user).first()
                    if obj:
                        obj.delete()
        return super().get(request)
