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


import re
from urllib.parse import urlparse

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from .collection import Collection
from .document import Document
from .models import WorkerStats
from .url import sanitize_url, validate_url
from .utils import human_datetime, plural
from .views import AdminView


def _add_unique_patterns(existing_regex, new_patterns):
    """Add new patterns to existing regex, avoiding duplicates."""
    if not new_patterns:
        return existing_regex

    # Get existing patterns as a set for deduplication check
    existing_patterns = set()
    if existing_regex:
        existing_patterns = {pattern.strip() for pattern in existing_regex.split("\n") if pattern.strip()}

    # Filter new patterns to only include those not already present
    new_pattern_list = [pattern.strip() for pattern in new_patterns.split("\n") if pattern.strip()]
    unique_new_patterns = [pattern for pattern in new_pattern_list if pattern not in existing_patterns]

    if not unique_new_patterns:
        return existing_regex

    # Append only the unique new patterns to existing content
    if existing_regex:
        return existing_regex + "\n" + "\n".join(unique_new_patterns)
    else:
        return "\n".join(unique_new_patterns)


def queue_urls(urls, collection, show_on_homepage, crawl_scope):
    """Queue URLs for crawling with the specified collection and scope
    settings."""
    # Extract hostnames if scope modification is requested
    if crawl_scope != AddToQueueForm.CRAWL_SCOPE_NO_CHANGE:
        hostnames = set()
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.hostname:
                    hostnames.add(parsed.hostname)
            except Exception:  # nosec B112
                continue

        # Add hostnames to appropriate regex field if we have any
        if hostnames:
            hostname_patterns = [f"^https?://{re.escape(hostname)}/.*" for hostname in hostnames]
            new_patterns = "\n".join(hostname_patterns)

            if crawl_scope == AddToQueueForm.CRAWL_SCOPE_UNLIMITED:
                # Add to unlimited_regex
                collection.unlimited_regex = _add_unique_patterns(collection.unlimited_regex, new_patterns)
            elif crawl_scope == AddToQueueForm.CRAWL_SCOPE_LIMITED:
                # Add to limited_regex
                collection.limited_regex = _add_unique_patterns(collection.limited_regex, new_patterns)

            collection.save()

    # Queue each URL
    for url in urls:
        Document.manual_queue(url, collection, show_on_homepage)


class AddToQueueForm(forms.Form):
    CRAWL_SCOPE_NO_CHANGE = "no_change"
    CRAWL_SCOPE_UNLIMITED = "unlimited"
    CRAWL_SCOPE_LIMITED = "limited"

    CRAWL_SCOPE_CHOICES = [
        (CRAWL_SCOPE_NO_CHANGE, "Keep collection settings unchanged"),
        (CRAWL_SCOPE_UNLIMITED, "Crawl entire websites (unlimited depth)"),
        (CRAWL_SCOPE_LIMITED, "Crawl websites with depth limit from collection settings"),
    ]

    urls = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 100%; padding-right: 0", "rows": "3", "autofocus": True}),
        label="URLs to crawl",
    )
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all(),
        required=True,
        label="Collection",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label=None,
    )
    crawl_scope = forms.ChoiceField(
        choices=CRAWL_SCOPE_CHOICES,
        initial=CRAWL_SCOPE_NO_CHANGE,
        widget=forms.RadioSelect,
        label="Crawling scope",
        help_text="Choose how to crawl the websites from these URLs",
    )
    show_on_homepage = forms.BooleanField(
        required=False,
        help_text="Display the initial document on the homepage",
        initial=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            default_collection = Collection.objects.get(name="Default")
            self.fields["collection"].initial = default_collection.pk
        except Collection.DoesNotExist:
            first_collection = Collection.objects.first()
            self.fields["collection"].initial = first_collection.pk

    def clean_urls(self):
        errors = []
        urls = []
        for line_no, line in enumerate(self.cleaned_data["urls"].splitlines()):
            url = line.strip()
            if not url:
                continue

            try:
                url = sanitize_url(url)
                validate_url(url)
            except Exception as e:
                errors.append(f"Line {line_no + 1}: {e.args[0]}")

            urls.append(url)
        if errors:
            raise ValidationError("Invalid URL" + plural(len(errors)) + ":\n" + "\n".join(errors))
        return urls


class AddToQueueView(AdminView, FormView):
    template_name = "admin/add_to_queue.html"
    title = "Crawl a new URL"
    form_class = AddToQueueForm
    permission_required = "se.add_document"
    admin_site = None

    def __init__(self, *args, **kwargs):
        self.admin_site = kwargs.pop("admin_site")
        super().__init__(*args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        # Pre-populate form fields from GET parameters
        if "urls" in self.request.GET:
            initial["urls"] = self.request.GET.get("urls")
        if "collection" in self.request.GET:
            try:
                collection_id = int(self.request.GET.get("collection"))
                if Collection.objects.filter(id=collection_id).exists():
                    initial["collection"] = collection_id
            except (ValueError, TypeError):
                pass
        if "show_on_homepage" in self.request.GET:
            initial["show_on_homepage"] = self.request.GET.get("show_on_homepage").lower() == "true"
        else:
            # Default value when no GET parameter is provided
            initial["show_on_homepage"] = True
        return initial

    def get_context_data(self, **kwargs):
        Collection.create_default()
        context = super().get_context_data(**kwargs)
        context.update(self.admin_site.each_context(self.request))
        form = context["form"]

        collections = Collection.objects.all()
        for collection in collections:
            if collection.recrawl_freq == Collection.RECRAWL_FREQ_CONSTANT:
                context["recrawl_every"] = human_datetime(collection.recrawl_dt_min)
            elif collection.recrawl_freq == Collection.RECRAWL_FREQ_ADAPTIVE:
                context.update(
                    {
                        "recrawl_min": human_datetime(collection.recrawl_dt_min),
                        "recrawl_max": human_datetime(collection.recrawl_dt_max),
                    }
                )
        return_url = reverse("admin:queue")
        return context | {
            "collections": collections,
            "return_url": return_url,
            "Collection": Collection,
            "form": form,
        }

    def form_valid(self, form):
        urls = form.cleaned_data["urls"]
        collection = form.cleaned_data["collection"]
        crawl_scope = form.cleaned_data["crawl_scope"]

        queue_urls(urls, collection, form.cleaned_data["show_on_homepage"], crawl_scope)

        url_count = len(urls)
        if url_count > 1:
            msg = f"{url_count} URLs were queued."
        else:
            msg = "URL was queued."
        WorkerStats.wake_up()
        messages.success(self.request, msg)
        return redirect(reverse("admin:crawl_queue"))
