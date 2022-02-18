import json
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .forms import SearchForm
from .models import Document


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
        'settings': settings
    })
    return ctx


def search(request):
    results = None
    paginated = None
    q = None

    form = SearchForm(request.GET)
    if form.is_valid() and form.cleaned_data['q']:
        q = form.cleaned_data['q']
        lang = form.cleaned_data['l']

        query = SearchQuery(q, config=lang)

        START_SEL = '&#"_&'
        STOP_SEL = '&_"#&'
        results = Document.objects.annotate(
            rank=SearchRank(models.F('vector'), query),
            headline=SearchHeadline('content', query, start_sel=START_SEL, stop_sel=STOP_SEL)
        ).exclude(rank__lte=0.01).order_by('-rank', 'title')

        paginator = Paginator(results, form.cleaned_data['ps'])
        page_number = request.GET.get('p')
        paginated = paginator.get_page(page_number)

        for res in paginated:
            entries = res.headline.split(START_SEL)
            h = []
            for i, entry in enumerate(entries):
                if i != 0:
                    h.append(mark_safe('<b>'))

                if STOP_SEL in entry:
                    a, b = entry.split(STOP_SEL, 1)
                    h.append(a)
                    h.append(mark_safe('</b>'))
                    h.append(b)
                else:
                    h.append(entry)
            res.headline = h
    else:
        form = SearchForm()

    context = get_context({
        'form': form,
        'results': results,
        'paginated': paginated,
        'q': q,
        'title': q,
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


def prefs(request):
    supported = Document.get_supported_langs()
    langs = {}
    for iso, lang in settings.MYSE_LANGDETECT_TO_POSTGRES.items():
        if lang['name'] in supported:
            langs[iso] = lang

    context = get_context({
        'title': 'Preferences',
        'supported_langs': json.dumps(langs)
    })
    return render(request, 'se/prefs.html', context)
