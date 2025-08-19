# Copyright 2025 Laurent Defert
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

from django.shortcuts import reverse

from .collection import Collection
from .tag import Tag
from .tags import AdminTagsView


class TagsListView(AdminTagsView):
    template_name = "se/components/tags_list.html"

    def _is_enabled(self, tag):
        query_params = self.request.GET
        if query_params.get("tag") is not None:
            if not query_params.get("tag"):
                tags = []
            else:
                tags_pk = query_params.getlist("tag")
                tags = Tag.objects.filter(pk__in=tags_pk)
        else:
            obj = self._get_obj()
            if obj:
                tags = self.tags.all()
            else:
                return False
        return tag in tags

    def _tag_link(self, tag):
        link = self.request.GET.get("link")
        if link == "admin":
            return reverse("admin:se_tag_change", args=(tag.id,))
        elif link == "search":
            return reverse("search_redirect") + f"?tag={tag.id}"
        else:
            raise ValueError("Invalid link type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        model_tags = []
        for tag in Tag.objects.order_by("name"):
            if self._is_enabled(tag):
                model_tags.append(tag)
                tag.href = self._tag_link(tag)

        obj = self._get_obj()
        if obj:
            if isinstance(obj, Collection):
                title = f"⭐ Tags of {obj.name}"
            else:
                title = f"⭐ Tags of {obj.get_title_label()}"
            obj_pk = obj.pk
        else:
            title = "⭐ Tags"
            obj_pk = 0

        django_admin = self.request.GET.get("django_admin") == "1"
        model = self._get_model()._meta.model_name
        if django_admin:
            tags_edit_onclick = f"show_tags('/admin_tags/{model}/0/')"
        else:
            tags_edit_onclick = f"show_tags('/archive_tags/{obj_pk}/')"
        return context | {
            "django_admin": django_admin,
            "model_tags": model_tags,
            "model_tags_pks": ",".join([str(tag.pk) for tag in model_tags]),
            "tags_edit_title": title,
            "tags_edit_onclick": tags_edit_onclick,
        }
