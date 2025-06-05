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

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import FormView

from .crawl_policy import CrawlPolicy
from .document import Document
from .domain_setting import DomainSetting
from .models import WorkerStats
from .tag_field import TagField
from .url import sanitize_url, validate_url
from .utils import human_datetime, plural
from .views import AdminView


class AddToQueueForm(forms.Form):
    urls = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 100%; padding-right: 0", "rows": "3"}),
        label="URLs to crawl",
    )

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


class AddToQueueConfirmForm(AddToQueueForm):
    crawl_policy_choice = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[],
        required=False,
    )
    tags = TagField(Document, None)
    recursion_depth = forms.IntegerField(min_value=0, required=False, help_text="Maximum depth of links to follow")
    show_on_homepage = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Display the initial document on the homepage",
    )
    show_on_homepage.widget.attrs.update({"checked": True})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get("data"):
            # Since crawl_policy_choice choices depend on the urls, we pop it to skip validation
            self.fields.pop("crawl_policy_choice")


class AddToQueueConfirmationView(AddToQueueView):
    form_class = AddToQueueConfirmForm

    def dispatch(self, request, *args, **kwargs):
        if request.method != "POST":
            return redirect(reverse("admin:queue"))
        return super().dispatch(request, *args, **kwargs)

    def get_urls(self):
        form = AddToQueueForm(self.request.POST)
        if not form.is_valid():
            return []
        return form.cleaned_data["urls"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]

        if not form.is_valid():
            return context

        urls = self.get_urls()
        crawl_policies = set()
        for url in urls:
            crawl_policy = CrawlPolicy.get_from_url(url)
            crawl_policies.add(crawl_policy)

        initial = {"urls": "\n".join(urls)}
        choices = []
        domain = None
        if len(urls) == 1:
            # In case the policy matches the default, we give the possibility to
            # create a new policy for the domain
            matching = CrawlPolicy.get_from_url(urls[0])
            if matching == CrawlPolicy.create_default() and matching.recursion != CrawlPolicy.CRAWL_ALL:
                if matching.recursion == CrawlPolicy.CRAWL_ON_DEPTH:
                    if matching.recursion_depth:
                        default_txt = f"<b>Follow links up to {matching.recursion_depth} level</b> (override below)"
                    else:
                        default_txt = "<b>Index only this URL</b> (or override <i>recursion depth</i> below)"
                elif matching.recursion == CrawlPolicy.CRAWL_NEVER:
                    default_txt = "<b>Index only this URL</b>"

                default_txt += ' using the policy <a href="{}">{}</a>'
                default_txt = format_html(
                    default_txt, reverse("admin:se_crawlpolicy_change", args=(matching.id,)), matching
                )
                choices.append(("default", default_txt))
                domain = self._domain_name(urls[0])
                choices.append(
                    (
                        "domain",
                        format_html("<b>Index all pages of https://{}/</b> (creates a new policy)", domain),
                    )
                )
                initial["crawl_policy_choice"] = "default"

        if len(crawl_policies) == 1:
            initial["recursion_depth"] = crawl_policy.recursion_depth

        form = AddToQueueConfirmForm(initial=initial)
        form.fields["crawl_policy_choice"].choices = choices

        urls = ["^" + re.escape(url) for url in self.get_urls()]

        context |= {
            "crawl_policies": sorted(crawl_policies, key=lambda x: x.url_regex),
            "crawl_policy": crawl_policy,
            "urls": urls,
            "CrawlPolicy": CrawlPolicy,
            "DomainSetting": DomainSetting,
            "form": form,
            "domain": domain,
        }

        if crawl_policy.recrawl_freq == CrawlPolicy.RECRAWL_FREQ_CONSTANT:
            context["recrawl_every"] = human_datetime(crawl_policy.recrawl_dt_min)
        elif crawl_policy.recrawl_freq == CrawlPolicy.RECRAWL_FREQ_ADAPTIVE:
            context.update(
                {
                    "recrawl_min": human_datetime(crawl_policy.recrawl_dt_min),
                    "recrawl_max": human_datetime(crawl_policy.recrawl_dt_max),
                }
            )

        return context

    def _domain_name(self, url):
        return re.match(r"https?://([^/]+)", url).group(1)

    def _create_domain_policy(self, url, tags):
        domain = self._domain_name(url)
        policy = CrawlPolicy.create_default()
        webhooks = list(policy.webhooks.all())
        policy.id = None
        policy.url_regex = f"^https?://{re.escape(domain)}/"
        policy.recursion = CrawlPolicy.CRAWL_ALL
        policy.save()
        policy.tags.set(tags)
        policy.webhooks.set(webhooks)

    def form_valid(self, form):
        if self.request.POST.get("action") == "Confirm":
            if self.request.POST.get("crawl_policy_choice") == "domain":
                self._create_domain_policy(form.cleaned_data["urls"][0], form.cleaned_data["tags"])

            urls = form.cleaned_data["urls"]
            for url in urls:
                show_on_homepage = bool(form.cleaned_data.get("show_on_homepage"))
                crawl_recurse = form.cleaned_data.get("recursion_depth")
                doc = Document.manual_queue(url, show_on_homepage, crawl_recurse)
                if self.request.POST.get("crawl_policy_choice") == "default":
                    doc.tags.set(form.cleaned_data["tags"])

            url_count = len(urls)
            if url_count > 1:
                msg = f"{url_count} URLs were queued."
            else:
                msg = "URL was queued."
            WorkerStats.wake_up()
            messages.success(self.request, msg)
            return redirect(reverse("admin:crawl_queue"))

        context = self.get_context_data()
        return self.render_to_response(context)
