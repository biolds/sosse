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

import csv
import datetime
import io
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.generic import View

from .models import SearchEngine
from .rest_api import SearchResult
from .search import get_documents_from_request
from .search_form import SearchForm


class CsvView(View):
    def _csv_is_allowed(self, request):
        if not settings.SOSSE_CSV_EXPORT:
            return False

        if request.user.is_authenticated:
            return True

        if settings.SOSSE_ANONYMOUS_SEARCH:
            return True

        return False

    def get(self, request):
        results = None
        q = None

        if not self._csv_is_allowed(request):
            raise PermissionDenied

        form = SearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data["q"]
            redirect_url = SearchEngine.should_redirect(q)
            if redirect_url:
                return HttpResponse(
                    b"External search cannot be performed",
                    content_type="text/plain",
                    status=400,
                )

            _, results, _ = get_documents_from_request(request, form)

            sort_key = request.GET.get("s", "")
            if sort_key.startswith("-"):
                sort_key = sort_key[1:]

            if sort_key not in ("crawl_first", "crawl_last"):
                sort_key = "crawl_first"

            param = {f"{sort_key}__isnull": True}
            results = results.exclude(**param)
            results = results.order_by("-" + sort_key)

            is_structured = False
            metadata_fields = set()

            docs = []
            for doc in results[: settings.SOSSE_CSV_EXPORT_SIZE]:
                doc = SearchResult(instance=doc)
                doc = deepcopy(doc.data)
                doc.pop("content")
                doc.pop("normalized_content")
                doc.pop("vector")
                doc.pop("vector_lang")

                # If all subelements of metadata are not structured, flatten it
                if not is_structured:
                    for v in doc["metadata"].values():
                        if isinstance(v, list) or isinstance(v, dict):
                            is_structured = True
                            break
                    else:
                        metadata_fields |= set(doc["metadata"].keys())

                docs.append(doc)

            if not is_structured:
                for doc in docs:
                    metadata = doc.pop("metadata")
                    for field in sorted(metadata_fields):
                        doc[f"metadata {field}"] = metadata.get(field, "")

            filedate = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_{q}_{filedate}.csv"
            if docs:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=docs[0].keys())
                writer.writeheader()
                writer.writerows(docs)
                return HttpResponse(
                    output.getvalue(),
                    content_type="text/csv",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Cache-Control": "no-cache",
                    },
                )
            else:
                return HttpResponse(
                    b"",
                    content_type="text/csv",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Cache-Control": "no-cache",
                    },
                )

        return HttpResponse(b"Invalid query parameters", content_type="text/plain", status=400)
