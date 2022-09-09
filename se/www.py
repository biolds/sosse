from django.shortcuts import render, reverse
from django.utils.html import format_html

from .models import Link
from .cached import get_document, get_context


def www(request, url):
    doc = get_document(url)

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
            l = l[link_pos + len(link.text or ''):]
            content_pos += len(txt) + len(link.text or '')

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

    context = get_context(doc)
    context['content'] = content

    if doc.screenshot_file:
        context['other_link'] = {
            'href': reverse('screenshot', args=[url]),
            'text': 'Screenshot'
        }
    return render(request, 'se/www.html', context)
