# Copyright 2022-2023 Laurent Defert
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

from django.shortcuts import render

from .cached import get_document, get_context
from .login import login_required
from .utils import reverse_no_escape


@login_required
def words(request, url):
    url = request.META['REQUEST_URI'][7:]
    doc = get_document(url)
    context = get_context(doc)
    words = []
    for w in doc.vector.split():
        word, weights = w.split(':', 1)
        word = word.strip("'")
        words.append((word, weights))

    context.update({
        'other_links': [{
            'href': reverse_no_escape('www', args=[url]),
            'text': 'Cached page',
        }, {
            'href': reverse_no_escape('screenshot', args=[url]),
            'text': 'Screenshot'
        }],
        'words': words,
        'lang': doc.lang_flag(True)
    })
    return render(request, 'se/words.html', context)
