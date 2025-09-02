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
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from .collection import Collection
from .document import Document
from .views import AdminView


class MoveToCollectionForm(forms.Form):
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all(),
        required=True,
        label="Destination Collection",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label=None,
    )


class MoveToCollectionView(AdminView, FormView):
    template_name = "admin/move_to_collection.html"
    title = "Move Documents to Collection"
    form_class = MoveToCollectionForm
    permission_required = "se.change_document"
    admin_site = None

    def __init__(self, *args, **kwargs):
        self.admin_site = kwargs.pop("admin_site")
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.admin_site.each_context(self.request))

        document_ids = self.request.session.get("documents_to_move", [])
        documents = Document.objects.wo_content().filter(id__in=document_ids)
        document_count = documents.count()

        context.update(
            {
                "documents": documents,
                "document_count": document_count,
                "return_url": reverse("admin:se_document_changelist"),
            }
        )
        return context

    def form_valid(self, form):
        document_ids = self.request.session.get("documents_to_move", [])
        if not document_ids:
            messages.error(self.request, "No documents selected.")
            return redirect(reverse("admin:se_document_changelist"))

        destination_collection = form.cleaned_data["collection"]
        documents = Document.objects.wo_content().filter(id__in=document_ids)
        document_count = documents.count()

        if document_count == 0:
            messages.error(self.request, "No documents found to move.")
        else:
            documents.update(collection=destination_collection)

            if document_count > 1:
                msg = f"{document_count} documents were moved to collection '{destination_collection.name}'."
            else:
                msg = f"Document was moved to collection '{destination_collection.name}'."
            messages.success(self.request, msg)

        del self.request.session["documents_to_move"]
        return redirect(reverse("admin:se_document_changelist"))

    def get(self, request, *args, **kwargs):
        document_ids = request.session.get("documents_to_move", [])
        if not document_ids:
            messages.error(request, "No documents selected.")
            return redirect(reverse("admin:se_document_changelist"))
        return super().get(request, *args, **kwargs)
