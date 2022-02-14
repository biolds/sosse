from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .forms import SearchForm
from .models import Document


def search(request):
    results = None
    paginated = None
    q = None

    form = SearchForm(request.GET)
    if form.is_valid() and form.cleaned_data['q']:
        q = form.cleaned_data['q']
        query = SearchQuery(q)

        START_SEL = '&#"_&'
        STOP_SEL = '&_"#&'
        results = Document.objects.annotate(
            rank=SearchRank(models.F('vector'), query),
            headline=SearchHeadline('content', query, start_sel=START_SEL, stop_sel=STOP_SEL)
        ).exclude(rank__lte=0.01).order_by('-rank')

        paginator = Paginator(results, settings.MYSE_RESULTS_COUNT)
        page_number = request.GET.get('page')
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

    context = {
        'form': form,
        'results': results,
        'paginated': paginated,
        'q': q
    }
    return render(request, 'se/index.html', context)
