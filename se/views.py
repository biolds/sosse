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

from dataclasses import dataclass
from random import choice
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from .login import SosseLoginRequiredMixin
from .online import online_status

ANIMALS = "🦓🦬🦣🦒🦦🦥🦘🦌🐢🦝🦭🦫🐆🐅🦎🐍🐘🦙🐫🐪🐏🐐🦛🦏🐂🐃🐎🐑🐒🦇🐖🐄🐛🐝🦧🦍🐜🐞🐌🦋🦗🐨🐯🦁🐮🐰🐻🐻‍❄️🐼🐶🐱🐭🐹🐗🐴🐷🐣🐥🐺🦊🐔🐧🐦🐤🐋🐊🐸🐵🐡🐬🦈🐳🦐🦪🐠🐟🐙🦑🦞🦀🦅🕊🦃🐓🦉🦤🦢🦆🪶🦜🦚🦩🐩🐕‍🦮🐕🐁🐀🐇🐈🦔🦡🦨🐿"


def format_url(request, params):
    """This function takes the current url and replaces query parameters by new
    values provided."""
    parsed_url = urlparse(request.get_full_path())
    query_string = parse_qs(parsed_url.query)
    for k, v in query_string.items():
        query_string[k] = v[0]

    for param in params.split("&"):
        val = None
        if "=" in param:
            key, val = param.split("=", 1)
        else:
            key = param

        if val:
            query_string[key] = val
        else:
            query_string.pop(key, None)

    qs = "&".join([f"{k}={v}" for k, v in query_string.items()])
    return parsed_url._replace(query=qs).geturl()


@dataclass
class RedirectException(Exception):
    url: str


class RedirectMixin:
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except RedirectException as e:
            return redirect(e.url)


class BaseView(RedirectMixin, SosseLoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["settings"] = settings
        if hasattr(self, "title"):
            context["title"] = self.title
        return context


class AdminView(PermissionRequiredMixin, BaseView):
    pass


class UserView(BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = ""
        while not animal:
            # choice sometimes returns an empty string for an unknown reason
            animal = choice(ANIMALS)  # nosec B311 random is not used for security purposes

        return context | {
            "animal": animal,
            "online_status": online_status(self.request),
        }

    def _get_pagination(self, paginated):
        context = {}
        if paginated and paginated.has_previous():
            context.update(
                {
                    "page_first": format_url(self.request, "p="),
                    "page_previous": format_url(self.request, f"p={paginated.previous_page_number()}"),
                }
            )
        if paginated and paginated.has_next():
            context.update(
                {
                    "page_next": format_url(self.request, f"p={paginated.next_page_number()}"),
                    "page_last": format_url(self.request, f"p={paginated.paginator.num_pages}"),
                }
            )

        return context
