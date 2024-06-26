# Copyright 2022-2024 Laurent Defert
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

import logging
import re
import uuid

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.html import escape

from .document import Document, remove_accent
from .forms import FILTER_FIELDS


logger = logging.getLogger('web')

FILTER_RE = '(ft|ff|fo|fv|fc)[0-9]+$'


def get_documents_from_request(request, form, stats_call=False):
    filters = {}
    for key, val in request.GET.items():
        if not re.match(FILTER_RE, key):
            continue

        filter_no = key[2:]
        f = filters.get(filter_no, {})
        f[key[:2]] = val
        filters[filter_no] = f
    keys = sorted(filters.keys())
    params = [filters[k] for k in keys]
    return get_documents(request, params, form, stats_call)


def get_documents(request, params, form, stats_call):
    REQUIRED_KEYS = ('ft', 'ff', 'fo', 'fv')

    results = Document.objects.all()
    has_query = False

    q = form.cleaned_data['q']
    q = remove_accent(q)
    query = None
    if q:
        has_query = True
        lang = form.cleaned_data['l']

        query = SearchQuery(q, config=lang, search_type='websearch')
        all_results = Document.objects.filter(vector=query).annotate(
            rank=SearchRank(models.F('vector'), query),
        )
        results = all_results.exclude(rank__lte=0.01)

        if results.count() == 0:
            results = all_results

    include_hidden = form.cleaned_data.get('i', False) and True

    if not request.user.has_perm('se.document_change') or not include_hidden:
        results = results.exclude(hidden=True)

    if settings.SOSSE_EXCLUDE_NOT_INDEXED:
        results = results.exclude(crawl_last__isnull=True)
    if settings.SOSSE_EXCLUDE_REDIRECT:
        results = results.filter(redirect_url__isnull=True)

    for f in params:
        cont = True
        for k in REQUIRED_KEYS:
            if not f.get(k):
                break
        else:
            cont = False
        if cont:
            continue

        has_query = True
        ftype = f['ft']
        field = f['ff']
        operator = f['fo']
        value = f['fv']
        case = f.get('fc', False) and True

        if operator == 'contain' and case:
            param = '__contains'
        elif operator == 'contain' and not case:
            param = '__icontains'
        elif operator == 'regexp' and case:
            param = '__regex'
        elif operator == 'regexp' and not case:
            param = '__iregex'
        elif operator == 'equal' and case:
            param = '__exact'
        elif operator == 'equal' and not case:
            param = '__iexact'
        else:
            raise Exception('Unknown operation %s' % operator)

        if field not in list(dict(FILTER_FIELDS).keys()):
            raise Exception('Invalid FILTER_FIELDS %s / %s' % (field, list(dict(FILTER_FIELDS).keys())))

        if field == 'doc':
            content_param = {'content' + param: value}
            title_param = {'title' + param: value}
            url_param = {'url' + param: value}
            qf = models.Q(**content_param) | models.Q(**title_param) | models.Q(**url_param)
        elif field in ('lto_url', 'lto_txt', 'lby_url', 'lby_txt'):
            field, rel_field = field.split('_')
            subfield = 'doc_to' if field == 'lto' else 'doc_from'
            field = 'links_to' if field == 'lto' else 'linked_from'
            if rel_field == 'url':
                key1 = f'{field}__{subfield}__url{param}'
                key2 = f'{field}__extern_url{param}'
                qf = models.Q(**{key1: value}) | models.Q(**{key2: value})
            else:
                key = f'{field}__text{param}'
                qf = models.Q(**{key: value})
        else:
            qparams = {field + param: value}
            qf = models.Q(**qparams)

        if ftype == 'exc':
            qf = ~qf
        elif ftype == 'inc':
            pass
        else:
            raise Exception('Query type %s not supported' % operator)

        logger.debug('filter %s %s', ftype, qf)
        results = results.filter(qf)

    doc_lang = form.cleaned_data.get('doc_lang')
    if doc_lang:
        results = results.filter(lang_iso_639_1=doc_lang)

    if not stats_call:
        order_by = form.cleaned_data['order_by']
        results = results.order_by(*order_by).distinct()

    if not has_query:
        results = Document.objects.none()

    return has_query, results, query


def fallback_headline(doc):
    lines = doc.content.splitlines()
    if lines:
        return lines[0]
    return ''


def add_headlines(paginated, query):
    for res in paginated:
        # rebuild the headline using non-normalized content
        if query:
            rnd = uuid.uuid1().hex
            pg_headline = Document.objects.filter(id=res.id).annotate(
                headline=SearchHeadline(
                    'normalized_content',
                    query,
                    start_sel='s' + rnd,
                    stop_sel='e' + rnd,
                )
            ).first()

            # find the location of the headline in the normalized content
            headline = pg_headline.headline.replace('s' + rnd, '')
            headline = headline.replace('e' + rnd, '')

            if headline not in res.normalized_content or \
                    's' + rnd not in pg_headline.headline or \
                    'e' + rnd not in pg_headline.headline:
                res.headline = fallback_headline(res)
                continue

            headline_idx = res.normalized_content.index(headline)
            src = pg_headline.headline
            dest = escape('')
            while src:
                txt, src = src.split('s' + rnd, 1)
                dest += escape(res.content[headline_idx:headline_idx + len(txt)])
                headline_idx += len(txt)

                match, src = src.split('e' + rnd, 1)
                dest += '<span class="res-highlight">'
                dest += escape(res.content[headline_idx:headline_idx + len(match)])
                headline_idx += len(match)
                dest += '</span>'

                if 's' + rnd not in src or 'e' + rnd not in src:
                    dest += res.content[headline_idx:len(src)]
                    break
            res.headline = mark_safe(dest)
        else:
            res.headline = fallback_headline(res)
    return paginated
