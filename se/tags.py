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

from django.apps import apps
from django.shortcuts import reverse
from django.views.generic.base import TemplateView

from .document import Document
from .login import SosseLoginRequiredMixin
from .search import get_documents_from_request
from .search_form import SearchForm
from .tag import Tag


class AdminTagsView(SosseLoginRequiredMixin, TemplateView):
    template_name = "se/tags.html"

    def _get_model(self):
        return apps.get_model("se", self.kwargs["model"])

    def _objs_queryset(self):
        model = self._get_model()
        if model == Document:
            return model.objects.wo_content()
        else:
            return model.objects.all()

    def _get_obj(self):
        if self.kwargs["pk"] == "0":
            return None
        return self._objs_queryset().get(pk=self.kwargs["pk"])

    def _is_enabled(self, tag):
        if not self._get_obj():
            return False
        return self._get_obj().tags.filter(pk=tag.pk).count()

    def _submit_onclick(self):
        model = self._get_model()
        tags_list = reverse("tags_list", kwargs={"model": model._meta.model_name, "pk": 0})
        return f"save_tags('{tags_list}?link=admin&django_admin=1', null)"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tag_change_permission = (
            self.request.user.has_perm("se.add_tag")
            or self.request.user.has_perm("se.change_tag")
            or self.request.user.has_perm("se.delete_tag")
        )

        tags = []
        for tag in Tag.objects.all():
            tag.disabled = not self._is_enabled(tag)
            tags.append(tag)

        root_tags = []
        for tag in Tag.get_root_nodes():
            tag.descendants = Tag.get_tree(tag)
            root_tags.append(tag)

        return context | {
            "change_permission": tag_change_permission,
            "create_tag_href": reverse("admin:se_tag_add"),
            "view_tags_href": reverse("admin:se_tag_changelist"),
            "tags": tags,
            "root_tags": root_tags,
            "tags_edit_submit_onclick": self._submit_onclick(),
            "tags_edit_submit_text": "✔ Ok",
        }


class ArchiveTagsView(AdminTagsView):
    def _get_model(self):
        return Document

    def _submit_onclick(self):
        model = self._get_model()
        if self._get_obj() is None:
            tags_list = reverse("tags_list", kwargs={"model": model._meta.model_name, "pk": 0})
        else:
            tags_list = reverse("tags_list", kwargs={"model": model._meta.model_name, "pk": self._get_obj().pk})

        save_tag_url = reverse(f"{model._meta.model_name}-detail", kwargs={"pk": self._get_obj().pk})
        return f"save_tags('{tags_list}?link=search', '{save_tag_url}')"


class SearchTagsView(AdminTagsView):
    def dispatch(self, request, *args, **kwargs):
        self.form = SearchForm(self.request.GET)
        return super().dispatch(request, *args, **kwargs)

    def _is_enabled(self, tag):
        if not self.form.is_valid():
            return False

        return tag in self.form.cleaned_data["tag"]

    def _objs_queryset(self):
        has_query, results, query = get_documents_from_request(self.request, self.form)

        if results.count():
            return results

        return Document.objects.wo_content()

    def _submit_onclick(self):
        return "submit_search()"

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(*args, **kwargs) | {
            "tags_edit_submit_onclick": "submit_search()",
            "tags_edit_submit_text": "🔍 Search",
        }
