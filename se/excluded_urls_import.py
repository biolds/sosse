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
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.views.generic import FormView

from .models import ExcludedUrl
from .views import AdminView


class ExcludedUrlForm(forms.Form):
    urls = forms.CharField(
        label="URLs",
        widget=forms.Textarea(attrs={"placeholder": "Enter URLs here, one per line...", "autofocus": True}),
        required=True,
        help_text="Enter one URL per line",
    )
    urls.widget.attrs.update({"style": "width: 50%; padding-right: 0"})
    starting_with = forms.BooleanField(label="Exclude all URLs starting with these patterns", required=False)
    comment = forms.CharField(
        label="Comment",
        widget=forms.Textarea(attrs={"placeholder": "Optional comment for these URLs..."}),
        required=False,
        help_text="Optional comment that will be applied to all imported URLs",
    )
    comment.widget.attrs.update({"style": "width: 50%; padding-right: 0; height: 80px"})

    def clean(self):
        self.cleaned_data = super().clean()
        urls_text = self.cleaned_data.get("urls", "").strip()

        if not urls_text:
            raise ValidationError("At least one URL must be provided")

        urls = []
        for line in urls_text.split("\n"):
            line = line.strip()
            if line:
                urls.append(line)

        if not urls:
            raise ValidationError("At least one URL must be provided")

        self.cleaned_data["urls_list"] = urls
        return self.cleaned_data


class ExcludedUrlsImportView(AdminView, FormView):
    template_name = "admin/excluded_urls_import.html"
    title = "Excluded URLs import"
    form_class = ExcludedUrlForm
    permission_required = "se.change_excludedurl"

    def form_valid(self, form):
        urls_list = form.cleaned_data["urls_list"]
        starting_with = form.cleaned_data.get("starting_with", False)
        comment = form.cleaned_data.get("comment", "")

        created_count = 0

        for url in urls_list:
            excluded_url, created = ExcludedUrl.objects.get_or_create(
                url=url, defaults={"starting_with": starting_with, "comment": comment}
            )
            if created:
                created_count += 1

        if created_count > 0:
            messages.success(self.request, f"{created_count} URLs added to exclusion list.")
        else:
            messages.info(self.request, "No changes were made (all URLs already existed).")

        return redirect("admin:se_excludedurl_changelist")
