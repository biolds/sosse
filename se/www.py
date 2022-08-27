from django.shortcuts import get_object_or_404, render, reverse
from django.utils.html import format_html, escape

from .models import Document, Link


def www(request, url):
    # re-establish double //
    scheme, url = url.split('/', 1)
    if url[0] != '/':
        url = '/' + url
    url = scheme + '/' + url

    doc = get_object_or_404(Document, url=url)

    content = format_html('')
    content_pos = 0
    links = list(Link.objects.filter(doc_from=doc).order_by('link_no'))
    link_no = 0
    for l in doc.content.splitlines():
        while link_no < len(links) and links[link_no].pos < content_pos + len(l):
            link = links[link_no]
            link_pos = link.pos - content_pos
            txt = l[:link_pos]
            l = l[link_pos + len(link.text):]
            content_pos += len(txt) + len(link.text)

            content += format_html('{}<a href="{}">{}</a> <a href="{}">🌍</a>',
                                    txt,
                                    reverse('www', args=(link.doc_to.url,)),
                                    link.text,
                                    link.doc_to.url)
            link_no += 1

        content_pos += len(l) + 1 # +1 for the \n stripped by splitlines()
        content += format_html('{}<br/>', l)

    context = {
        'doc': doc,
        'page_title': doc.title,
        'content': content,
    }
    if doc.favicon and not doc.favicon.missing:
        context['favicon'] = reverse('favicon', args=(doc.favicon.id,))

    return render(request, 'se/www.html', context)
