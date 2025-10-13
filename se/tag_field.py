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

from django import forms
from django.forms.widgets import CheckboxSelectMultiple
from django.template.loader import render_to_string
from django.urls import reverse

from .collection import Collection
from .tag import Tag


class TagWidget(CheckboxSelectMultiple):
    def __init__(self, model, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.instance = instance

    def render(self, name, value, attrs=None, renderer=None):
        model_name = None
        tags = []

        model_name = self.model._meta.model_name

        if value:
            for tag_id in value:
                if not tag_id:
                    # If no tag is selected, the value is an empty string during collection creation
                    continue
                tag = Tag.objects.get(pk=tag_id)
                tag.href = reverse("admin:se_tag_change", args=(tag_id,))
                tags.append(tag)

        if self.instance and self.instance.pk:
            if self.model == Collection:
                title = f"⭐ Tags of {self.instance.name}"
            else:
                title = f"⭐ Tags of {self.instance.get_title_label()}"
        else:
            title = "⭐ Tags"
        tags_url = f"'/admin_tags/{model_name}/0/'"
        return render_to_string(
            "se/components/tags_list.html",
            {
                "model_tags": tags,
                "model_tags_pks": ",".join([str(tag.pk) for tag in tags]),
                "django_admin": True,
                "tags_edit_title": title,
                "tags_edit_onclick": f"show_tags({tags_url})",
            },
        )


class TagField(forms.ModelMultipleChoiceField):
    def __init__(self, model, instance, *args, **kwargs):
        kwargs |= {"queryset": Tag.objects.all(), "required": False, "widget": TagWidget(model, instance)}
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if value and isinstance(value, list):
            value = value[0]
            if not value:
                # In case no tag is selected, the value is an empty string
                return []
            return [int(tag_id) for tag_id in value.split(",")]
        return []
