from django.shortcuts import render, reverse
from django.utils.html import format_html

from .cached import get_document, get_context
from .login import login_required
from .models import Link


@login_required
def www(request, url):
    # Keep the url with parameters
    url = request.META['REQUEST_URI'][5:]
    doc = get_document(url)

    content = format_html('')
    content_pos = 0

    links = Link.objects.filter(doc_from=doc).order_by('link_no')
    links_count = Link.objects.filter(doc_from=doc).count()
    link_no = 0
    for line in doc.content.splitlines():
        while link_no < links_count and links[link_no].pos < content_pos + len(line):
            link = links[link_no]
            link_pos = link.pos - content_pos
            txt = line[:link_pos]
            line = line[link_pos + len(link.text or ''):]
            content_pos += len(txt) + len(link.text or '')

            if link.doc_to:
                content += format_html('{}<a href="{}">{}</a> · <a href="{}">🌍</a>',
                                       txt,
                                       link.doc_to.get_absolute_url(),
                                       link.text,
                                       link.doc_to.url)
            else:
                content += format_html('{} [{}] · <a href="{}">🌍</a>',
                                       txt,
                                       link.text,
                                       link.extern_url)
            link_no += 1

        content_pos += len(line) + 1  # +1 for the \n stripped by splitlines()
        content += format_html('{}<br/>', line)

    context = get_context(doc)
    context['content'] = content

    if doc.screenshot_file:
        context['other_links'] = [{
            'href': reverse('screenshot', args=[url]),
            'text': 'Screenshot'
        }, {
            'href': reverse('words', args=[url]),
            'text': 'Words weight',
        }]
    return render(request, 'se/www.html', context)
