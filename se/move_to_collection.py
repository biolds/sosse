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
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from .collection import Collection
from .document import Document
from .views import AdminView


class MoveToCollectionForm(forms.Form):
    CONFLICT_SKIP = "skip"
    CONFLICT_OVERWRITE = "overwrite"
    CONFLICT_DELETE_SOURCE = "delete_source"

    CONFLICT_CHOICES = [
        (CONFLICT_SKIP, "Skip conflicting documents"),
        (CONFLICT_OVERWRITE, "Overwrite documents in destination collection"),
        (CONFLICT_DELETE_SOURCE, "Delete source document"),
    ]

    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all(),
        required=True,
        label="Destination Collection",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label=None,
    )

    conflict_resolution = forms.ChoiceField(
        choices=CONFLICT_CHOICES,
        initial=CONFLICT_OVERWRITE,
        required=True,
        label="When URL conflicts occur",
        widget=forms.Select(attrs={"class": "form-control"}),
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
        conflict_resolution = form.cleaned_data["conflict_resolution"]
        documents = Document.objects.wo_content().filter(id__in=document_ids)
        document_count = documents.count()

        if document_count == 0:
            messages.error(self.request, "No documents found to move.")
        else:
            moved_count = 0
            skipped_count = 0
            overwritten_count = 0
            deleted_count = 0

            with transaction.atomic():
                for document in documents:
                    # Skip documents that are already in the destination collection
                    if document.collection == destination_collection:
                        continue

                    # Check if a document with the same URL already exists in destination collection
                    existing_doc = (
                        Document.objects.wo_content()
                        .filter(url=document.url, collection=destination_collection)
                        .first()
                    )

                    if existing_doc:
                        if conflict_resolution == MoveToCollectionForm.CONFLICT_SKIP:
                            skipped_count += 1
                            continue
                        elif conflict_resolution == MoveToCollectionForm.CONFLICT_OVERWRITE:
                            # Delete the existing document first
                            existing_doc.delete()
                            overwritten_count += 1
                        elif conflict_resolution == MoveToCollectionForm.CONFLICT_DELETE_SOURCE:
                            # Delete the source document instead of moving it
                            document.delete()
                            deleted_count += 1
                            continue

                    # Move the document
                    document.collection = destination_collection
                    document.save()
                    moved_count += 1

            # Build success message
            message_parts = []
            if moved_count > 0:
                message_parts.append(f"{moved_count} document{'s' if moved_count > 1 else ''} moved")
            if overwritten_count > 0:
                message_parts.append(f"{overwritten_count} document{'s' if overwritten_count > 1 else ''} overwritten")
            if deleted_count > 0:
                message_parts.append(f"{deleted_count} source document{'s' if deleted_count > 1 else ''} deleted")
            if skipped_count > 0:
                message_parts.append(
                    f"{skipped_count} document{'s' if skipped_count > 1 else ''} skipped due to conflicts"
                )

            if message_parts:
                message = (
                    f"Operation completed: {', '.join(message_parts)} to collection '{destination_collection.name}'."
                )
                messages.success(self.request, message)
            else:
                messages.warning(self.request, "No documents were processed.")

        del self.request.session["documents_to_move"]
        return redirect(reverse("admin:se_document_changelist"))

    def get(self, request, *args, **kwargs):
        document_ids = request.session.get("documents_to_move", [])
        if not document_ids:
            messages.error(request, "No documents selected.")
            return redirect(reverse("admin:se_document_changelist"))
        return super().get(request, *args, **kwargs)
