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

import json

from django.db import connection
from django.http import HttpResponse
from django.views.generic import View

from .document import Document, remove_accent
from .login import LoginRequiredMixin
from .search import get_documents_from_request
from .search_form import SearchForm
from .utils import human_nb
from .views import format_url


class WordStatsView(LoginRequiredMixin, View):
    def get(self, request):
        results = None
        form = SearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data["q"]
            q = remove_accent(q)
            _, doc_query, _ = get_documents_from_request(request, form, True)
            doc_query = doc_query.values("vector")

            # Hack to obtain final SQL query, as described there:
            # https://code.djangoproject.com/ticket/17741#comment:4
            sql, params = doc_query.query.sql_with_params()
            cursor = connection.cursor()
            cursor.execute("EXPLAIN " + sql, params)
            raw_query = cursor.db.ops.last_executed_query(cursor, sql, params)
            raw_query = raw_query[len("EXPLAIN ") :]

            results = Document.objects.raw(
                "SELECT 1 AS id, word, ndoc FROM ts_stat(%s) ORDER BY ndoc DESC, word ASC LIMIT 100",
                (raw_query,),
            )
            results = [
                (
                    e.word,
                    human_nb(e.ndoc),
                    format_url(request, f"q={q} {e.word}")[len("/word_stats") :],
                )
                for e in list(results)
            ]
            results = json.dumps(results)

        return HttpResponse(results, content_type="application/json")
