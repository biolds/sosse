from hashlib import md5
from lxml.etree import Element, tostring

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.urls import reverse

from .forms import SearchForm
from .models import SearchEngine
from .search import get_documents


def elem(tag, text, **attr):
    e = Element(tag, **attr)
    if text is not None:
        e.text = text
    return e


def str_to_uuid(s):
    s = md5(s.encode('utf-8')).hexdigest()
    s = s[:8] + '-' + s[8:12] + '-' + s[12:16] + '-' + s[16:20] + '-' + s[20:]
    s = 'urn:uuid:' + s
    return s


def atom(request):
    results = None
    q = None

    form = SearchForm(request.GET)
    if form.is_valid():
        q = form.cleaned_data['q']
        redirect_url = SearchEngine.should_redirect(q)
        if redirect_url:
            return HttpResponse('External search cannot be performed', content_type='text/plain', status=400)

        results = get_documents(request, form)

        key = request.GET.get('s', '')
        if key.startswith('-'):
            key = key[1:]

        if key not in ('crawl_first', 'crawl_last'):
            key = 'crawl_first'

        param = {'%s__isnull' % key: True}
        results = results.exclude(**param)
        results = results.order_by('-' + key)

        base_url = request.META['REQUEST_SCHEME'] + '://' + request.META['HTTP_HOST']
        cached_page = request.GET.get('cached', '0')

        feed = Element('feed')
        feed.attrib['xmlns'] = 'http://www.w3.org/2005/Atom'
        feed.append(elem('title', f'OSSE · {q}'))
        feed.append(elem('description', f'OSSE search results for {q}'))
        url = base_url + reverse('search') + '?' + request.META['QUERY_STRING']
        feed.append(elem('link', None, href=url))
        if len(results):
            feed.append(elem('updated', getattr(results[0], key).isoformat()))
        feed_id = 'OSSE' + request.META['QUERY_STRING']
        feed.append(elem('id', str_to_uuid(feed_id)))
        feed.append(elem('icon', base_url + settings.STATIC_URL + 'favicon.svg'))

        for doc in results[:settings.OSSE_ATOM_FEED_SIZE]:
            entry = Element('entry')
            entry.append(elem('title', doc.title))
            if cached_page == '0':
                url = doc.url
            else:
                url = base_url + reverse('www', args=[doc.url])
            entry.append(elem('link', None, href=url))
            entry.append(elem('id', str_to_uuid(url)))
            entry.append(elem('updated', getattr(doc, key).isoformat()))

            content = ''
            lines = doc.content.splitlines()
            if lines:
                content = '\n'.join(lines[:5])
            entry.append(elem('summary', content))
            feed.append(entry)

        return HttpResponse(tostring(feed, pretty_print=True), content_type='text/plain')

    return HttpResponse('Invalid query parameters', content_type='text/plain', status=400)
