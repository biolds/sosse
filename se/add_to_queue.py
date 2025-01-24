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

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.generic import FormView

from .crawl_policy import CrawlPolicy
from .document import Document
from .domain_setting import DomainSetting
from .url import sanitize_url, validate_url
from .utils import human_datetime, plural
from .views import AdminView


class AddToQueueForm(forms.Form):
    urls = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 100%; padding-right: 0", "rows": "3"}),
        label="URLs to crawl",
    )
    recursion_depth = forms.IntegerField(min_value=0, required=False, help_text="Maximum depth of links to follow")
    show_on_homepage = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Display the initial document on the homepage",
    )
    show_on_homepage.widget.attrs.update({"checked": True})

    def __init__(self, data=None, *args, **kwargs):
        if data and not data.get("confirmation"):
            data = data.copy()
            data["recursion_depth"] = kwargs.get("initial", {}).get("recursion_depth")

        super().__init__(data, *args, **kwargs)

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.admin_site.each_context(self.request))
        context["form"].fields["urls"].widget.attrs.update({"autofocus": True})
        return context


class AddToQueueConfirmationView(AddToQueueView):
    def dispatch(self, request, *args, **kwargs):
        if request.method != "POST":
            return redirect(reverse("admin:queue"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"].fields["urls"].widget.attrs.pop("autofocus")
        return context

    def form_valid(self, form):
        if self.request.POST.get("action") == "Confirm":
            crawl_recurse = form.cleaned_data.get("recursion_depth")

            urls = form.cleaned_data["urls"]
            for url in urls:
                recursion_depth = crawl_recurse
                if recursion_depth is None:
                    crawl_policy = CrawlPolicy.get_from_url(url)
                    recursion_depth = crawl_policy.recursion_depth

                doc, created = Document.objects.get_or_create(url=url, defaults={"crawl_recurse": recursion_depth})
                if not created:
                    doc.crawl_next = now()
                    if recursion_depth:
                        doc.recursion_depth = recursion_depth

                doc.show_on_homepage = bool(form.cleaned_data.get("show_on_homepage"))
                doc.save()
            url_count = len(urls)
            if url_count > 1:
                msg = f"{url_count} URL{plural(url_count)} were queued."
            else:
                msg = "URL was queued."
            messages.success(self.request, msg)
            return redirect(reverse("admin:crawl_queue"))

        crawl_policies = set()
        for url in form.cleaned_data["urls"]:
            crawl_policy = CrawlPolicy.get_from_url(url)
            crawl_policies.add(crawl_policy)

        initial = {}
        if len(crawl_policies) == 1:
            initial = {"recursion_depth": crawl_policy.recursion_depth}

        form = AddToQueueForm(self.request.POST, initial=initial)
        form.is_valid()

        context = self.get_context_data(form=form)
        context.update(
            {
                "crawl_policies": sorted(crawl_policies, key=lambda x: x.url_regex),
                "crawl_policy": crawl_policy,
                "urls": form.cleaned_data["urls"],
                "CrawlPolicy": CrawlPolicy,
                "DomainSetting": DomainSetting,
                "form": form,
            }
        )
        if crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_CONSTANT:
            context["recrawl_every"] = human_datetime(crawl_policy.recrawl_dt_min)
        elif crawl_policy.recrawl_mode == CrawlPolicy.RECRAWL_ADAPTIVE:
            context.update(
                {
                    "recrawl_min": human_datetime(crawl_policy.recrawl_dt_min),
                    "recrawl_max": human_datetime(crawl_policy.recrawl_dt_max),
                }
            )
        return self.render_to_response(context)
