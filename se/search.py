import re

from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import models

from .models import Document, remove_accent


def get_documents(request, form, stats_call=False):
    FILTER_RE = '(ft|ff|fo|fv|fc)[0-9]+$'
    REQUIRED_KEYS = ('ft', 'ff', 'fo', 'fv')

    results = Document.objects.all()
    has_query = False

    q = remove_accent(form.cleaned_data['q'])
    if q:
        has_query = True
        lang = form.cleaned_data['l']
        query = SearchQuery(q, config=lang, search_type='websearch')
        results = Document.objects.filter(vector=query).annotate(
            rank=SearchRank(models.F('vector'), query),
        ).exclude(rank__lte=0.01)

    if settings.OSSE_EXCLUDE_NOT_INDEXED:
        results = results.exclude(crawl_last__isnull=True)
    if settings.OSSE_EXCLUDE_REDIRECT:
        results = results.filter(redirect_url__isnull=True)

    filters = {}
    for key, val in request.GET.items():
        if not re.match(FILTER_RE, key):
            continue

        filter_no = key[2:]
        f = filters.get(filter_no, {})
        f[key[:2]] = val
        filters[filter_no] = f

    for f in filters.values():
        cont = True
        for k in REQUIRED_KEYS:
            if not f.get(k):
                break
        else:
            cont = False
        if cont:
            continue

        has_query=True
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

        results = results.filter(qf)

    doc_lang = form.cleaned_data.get('doc_lang')
    if doc_lang:
        results = results.filter(lang_iso_639_1=doc_lang)

    if not stats_call:
        order_by = form.cleaned_data['order_by']
        results = results.order_by(*order_by).distinct()
    return has_query, results
