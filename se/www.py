from django.shortcuts import get_object_or_404, render, reverse
from django.utils.html import format_html, escape

from .models import Document, Link, UrlPolicy


def www(request, url):
    # re-establish double //
    scheme, url = url.split('/', 1)
    if url[0] != '/':
        url = '/' + url
    url = scheme + '/' + url

    doc = get_object_or_404(Document, url=url)

    content = format_html('')
    content_pos = 0

    links = Link.objects.filter(doc_from=doc).order_by('link_no')
    links_count = Link.objects.filter(doc_from=doc).count()
    link_no = 0
    for l in doc.content.splitlines():
        while link_no < links_count and links[link_no].pos < content_pos + len(l):
            link = links[link_no]
            link_pos = link.pos - content_pos
            txt = l[:link_pos]
            l = l[link_pos + len(link.text):]
            content_pos += len(txt) + len(link.text)

            if link.doc_to:
                content += format_html('{}<a href="{}">{}</a> · <a href="{}">🌍</a>',
                                        txt,
                                        reverse('www', args=(link.doc_to.url,)),
                                        link.text,
                                        link.doc_to.url)
            else:
                content += format_html('{} [{}] · <a href="{}">🌍</a>',
                                        txt,
                                        link.text,
                                        link.extern_url)
            link_no += 1

        content_pos += len(l) + 1 # +1 for the \n stripped by splitlines()
        content += format_html('{}<br/>', l)

    url_policy = UrlPolicy.get_from_url(doc.url)

    should_crawl = None
    if not url_policy.no_crawl and doc.crawl_depth is not None:
        should_crawl, _ = Document._should_crawl(url_policy,
                                                 doc.crawl_depth + 1,
                                                 doc.url)

    title = doc.title or doc.url
    page_title = None
    favicon = None
    if doc.favicon and not doc.favicon.missing:
        favicon = reverse('favicon', args=(doc.favicon.id,))
        page_title = format_html('<img src="{}" style="height: 32px; width: 32px; vertical-align: bottom" alt="icon"> {}', favicon, title)

    context = {
        'url_policy': url_policy,
        'should_crawl': should_crawl,
        'doc': doc,
        'head_title': title,
        'page_title': page_title or title,
        'content': content,
        'favicon': favicon
    }

    return render(request, 'se/www.html', context)
