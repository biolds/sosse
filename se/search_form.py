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

from django import forms
from django.conf import settings
from django.http import QueryDict

from .collection import Collection
from .document import Document
from .tag import Tag

SORT = (
    ("-rank", "Most relevant first"),
    ("rank", "Most relevant last"),
    ("modified_date", "Last modified ascending"),
    ("-modified_date", "Last modified descending"),
    ("crawl_first", "First crawled ascending"),
    ("-crawl_first", "First crawled descending"),
    ("crawl_last", "Last crawled ascending"),
    ("-crawl_last", "Last crawled descending"),
    ("title", "Title ascending"),
    ("-title", "Title descending"),
    ("url", "URL ascending"),
    ("-url", "URL descending"),
)
FILTER_FIELDS = (
    ("doc", "Document"),
    ("content", "Content"),
    ("title", "Title"),
    ("url", "URL"),
    ("mimetype", "Mimetype"),
    ("lto_url", "Links to url"),
    ("lto_txt", "Links to text"),
    ("lby_url", "Linked by url"),
    ("lby_txt", "Linked by text"),
    ("tag", "Tag"),
)


class SearchForm(forms.Form):
    q = forms.CharField(
        label="Search",
        required=False,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )
    l = forms.CharField(widget=forms.HiddenInput, initial="en", required=False)  # noqa
    ps = forms.IntegerField(
        widget=forms.HiddenInput,
        initial=settings.SOSSE_DEFAULT_PAGE_SIZE,
        required=False,
    )
    c = forms.ChoiceField(widget=forms.HiddenInput, choices=(("", ""), ("1", "1")), required=False)
    s = forms.ChoiceField(initial="-rank", choices=SORT, required=False)
    o = forms.ChoiceField(
        widget=forms.HiddenInput,
        choices=(("", ""), ("o", "o"), ("l", "l")),
        required=False,
    )
    i = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    collection = forms.ChoiceField(choices=[], required=False)
    tag = forms.MultipleChoiceField(widget=forms.MultipleHiddenInput, choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["collection"].choices = [("", "Any")] + [
            (str(a), b) for a, b in Collection.objects.values_list("id", "name")
        ]
        self.fields["tag"].choices = [(str(a), b) for a, b in Tag.objects.values_list("id", "name")]

    def clean(self):
        cleaned_data = super().clean()

        lang_iso = cleaned_data.get("l", "en")
        pg_lang = settings.SOSSE_LANGDETECT_TO_POSTGRES.get(lang_iso, {}).get("name")

        if pg_lang not in Document.get_supported_langs():
            pg_lang = settings.SOSSE_FAIL_OVER_LANG

        cleaned_data["l"] = pg_lang

        page_size = cleaned_data.get("ps", settings.SOSSE_DEFAULT_PAGE_SIZE) or settings.SOSSE_DEFAULT_PAGE_SIZE
        page_size = min(page_size, settings.SOSSE_MAX_PAGE_SIZE)
        cleaned_data["ps"] = page_size

        doc_lang = self.data.get("doc_lang")
        if doc_lang in settings.SOSSE_LANGDETECT_TO_POSTGRES:
            cleaned_data["doc_lang"] = doc_lang

        if settings.SOSSE_SEARCH_STRIP:
            q = cleaned_data["q"]
            if q.startswith(settings.SOSSE_SEARCH_STRIP):
                q = q[len(settings.SOSSE_SEARCH_STRIP) :]
            if q.endswith(settings.SOSSE_SEARCH_STRIP):
                q = q[: -len(settings.SOSSE_SEARCH_STRIP)]
            cleaned_data["q"] = q

        if cleaned_data["q"]:
            order_by = ("-rank", "title")
        else:
            order_by = ("title",)

        order = self.data.get("s")
        if order:
            _order = order
            if _order.startswith("-"):
                _order = _order[1:]
            if _order == "rank":
                if cleaned_data["q"]:
                    order_by = (order, "title")
            elif _order in ("crawl_first", "crawl_last"):
                order_by = (order, "title")
            elif _order in ("title", "url"):
                if cleaned_data["q"]:
                    order_by = (order, "-rank")
                else:
                    order_by = (order,)
        cleaned_data["order_by"] = order_by

        cleaned_data["c"] = bool(cleaned_data["c"])
        if isinstance(self.data, QueryDict):
            tags = self.data.getlist("tag")
        elif isinstance(self.data, dict):
            tags = self.data.get("tag", [])
        else:
            raise Exception("Unknown data type")

        cleaned_data["tag"] = Tag.objects.filter(id__in=tags)
        return cleaned_data
