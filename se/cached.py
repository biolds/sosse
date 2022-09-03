from django.shortcuts import get_object_or_404, reverse
from django.utils.html import format_html

from .models import Document, UrlPolicy


def get_document(url):
    # re-establish double //
    scheme, url = url.split('/', 1)
    if url[0] != '/':
        url = '/' + url
    url = scheme + '/' + url
    return get_object_or_404(Document, url=url)


def get_context(doc):
    url_policy = UrlPolicy.get_from_url(doc.url)
    title = doc.title or doc.url
    page_title = None
    favicon = None
    if doc.favicon and not doc.favicon.missing:
        favicon = reverse('favicon', args=(doc.favicon.id,))
        page_title = format_html('<img src="{}" style="height: 32px; width: 32px; vertical-align: bottom" alt="icon"> {}', favicon, title)

    return {
        'url_policy': url_policy,
        'doc': doc,
        'head_title': title,
        'page_title': page_title or title,
        'favicon': favicon
    }

