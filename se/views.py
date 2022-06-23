from collections import OrderedDict
import json
import re
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db import connection, models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .forms import SearchForm
from .models import Document, FavIcon, SearchEngine, remove_accent


def human_nb(nb):
    unit = ('', 'k', 'M', 'G', 'T', 'P')
    unit_no = 0

    while nb > 1000:
        nb /= 1000
        unit_no += 1
    return '%i%s' % (nb, unit[unit_no])


def format_url(request, params):
    parsed_url = urlparse(request.get_full_path())
    query_string = parse_qs(parsed_url.query)
    for k, v in query_string.items():
        query_string[k] = v[0]

    for param in params.split('&'):
        val = None
        if '=' in param:
            key, val = param.split('=', 1)
        else:
            key = param

        if val:
            query_string[key] = val
        else:
            query_string.pop(key, None)

    qs = '&'.join([f'{k}={v}' for k, v in query_string.items()])
    return parsed_url._replace(query=qs).geturl()

def get_context(ctx):
    ctx.update({
        'settings': settings,
        'favicon': '%s/se/bubble.svg' % settings.STATIC_URL
    })
    return ctx


def get_documents(request, form):
    FILTER_RE = '(ft|ff|fo|fv|fc)[0-9]+$'
    REQUIRED_KEYS = ('ft', 'ff', 'fo', 'fv')

    all_results = Document.objects.exclude(crawl_last__isnull=True)
    results = all_results
    q = remove_accent(form.cleaned_data['q'])
    if q:
        lang = form.cleaned_data['l']
        query = SearchQuery(q, config=lang, search_type='websearch')
        results = Document.objects.filter(vector=query).annotate(
            rank=SearchRank(models.F('vector'), query),
        ).exclude(rank__lte=0.01).order_by('-rank', 'title')

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
            raise Exception('Operation %s not supported' % operator)

        if field == 'doc':
            content_param = {'content' + param: value}
            title_param = {'title' + param: value}
            url_param = {'url' + param: value}
            qf = models.Q(**content_param) | models.Q(**title_param) | models.Q(**url_param)
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
    if results == all_results:
        return []
    return results


def search(request):
    results = None
    paginated = None
    q = None

    form = SearchForm(request.GET)
    if form.is_valid():
        q = form.cleaned_data['q']
        redirect_url = SearchEngine.should_redirect(q)
        if redirect_url:
            return redirect(redirect_url)

        results = get_documents(request, form)
        paginator = Paginator(results, form.cleaned_data['ps'])
        page_number = request.GET.get('p')
        paginated = paginator.get_page(page_number)

        for res in paginated:
            res.headline = ''
            lines = res.content.splitlines()
            if lines:
                res.headline = lines[0]
    else:
        form = SearchForm()

    myse_langdetect_to_postgres = OrderedDict()
    for key, val in sorted(settings.MYSE_LANGDETECT_TO_POSTGRES.items(), key=lambda x: x[1]['name']):
        if not Document.objects.filter(lang_iso_639_1=key).exists():
            continue
        myse_langdetect_to_postgres[key] = val

    context = get_context({
        'form': form,
        'results': results,
        'results_count': human_nb(len(results)),
        'paginated': paginated,
        'q': q,
        'title': q,
        'myse_langdetect_to_postgres': myse_langdetect_to_postgres
    })
    if paginated and paginated.has_previous():
        context.update({
            'page_first': format_url(request, 'p='),
            'page_previous': format_url(request, 'p=%i' % paginated.previous_page_number()),
        })
    if paginated and paginated.has_next():
        context.update({
            'page_next': format_url(request, 'p=%i' % paginated.next_page_number()),
            'page_last': format_url(request, 'p=%i' % paginated.paginator.num_pages)
        })
    return render(request, 'se/index.html', context)


def word_stats(request):
    results = None
    form = SearchForm(request.GET)
    if form.is_valid():
        q = form.cleaned_data['q']
        q = remove_accent(q)
        doc_query = get_documents(request, form).values('vector')

        # Hack to obtain final SQL query, as described there:
        # https://code.djangoproject.com/ticket/17741#comment:4
        sql, params = doc_query.query.sql_with_params()
        cursor = connection.cursor()
        cursor.execute('EXPLAIN ' + sql, params)
        raw_query = cursor.db.ops.last_executed_query(cursor, sql, params)
        raw_query = raw_query[len('EXPLAIN '):]

        results = Document.objects.raw('SELECT 1 AS id, word, ndoc FROM ts_stat(%s) ORDER BY ndoc DESC, word ASC LIMIT 100', (raw_query,))
        results = [(e.word, human_nb(e.ndoc), format_url(request, 'q=%s %s' % (q, e.word))[len('/word_stats'):]) for e in list(results)]
        results = json.dumps(results)

    return HttpResponse(results, content_type='application/json')


def prefs(request):
    supported_langs = json.dumps(Document.get_supported_lang_dict())
    context = get_context({
        'title': 'Preferences',
        'supported_langs': supported_langs
    })
    return render(request, 'se/prefs.html', context)


def favicon(request, favicon_id):
    fav = get_object_or_404(FavIcon, id=favicon_id)
    return HttpResponse(fav.content, content_type=fav.mimetype)
