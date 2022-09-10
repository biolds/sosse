from collections import OrderedDict
import json
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.core.paginator import Paginator
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .forms import SearchForm
from .models import Document, FavIcon, SearchEngine, remove_accent
from .search import get_documents


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
        'favicon': '%s/se/favicon.svg' % settings.STATIC_URL
    })
    return ctx


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

        has_query, results = get_documents(request, form)
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

    osse_langdetect_to_postgres = OrderedDict()
    for key, val in sorted(settings.OSSE_LANGDETECT_TO_POSTGRES.items(), key=lambda x: x[1]['name']):
        if not Document.objects.filter(lang_iso_639_1=key).exists():
            continue
        osse_langdetect_to_postgres[key] = val

    context = get_context({
        'hide_title': True,
        'form': form,
        'results': results,
        'results_count': human_nb(len(results)),
        'paginated': paginated,
        'has_query': has_query,
        'q': q,
        'page_title': q,
        'osse_langdetect_to_postgres': osse_langdetect_to_postgres
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
        _, doc_query = get_documents(request, form, True)
        doc_query = doc_query.values('vector')

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
        'page_title': 'Preferences',
        'supported_langs': supported_langs
    })
    return render(request, 'se/prefs.html', context)


def favicon(request, favicon_id):
    fav = get_object_or_404(FavIcon, id=favicon_id)
    return HttpResponse(fav.content, content_type=fav.mimetype)
