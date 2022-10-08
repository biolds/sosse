from django.conf import settings
from django.shortcuts import render, reverse

from .browser import SeleniumBrowser
from .cached import get_document, get_context


def screenshot(request, url):
    # Keep the url with parameters
    url = request.META['REQUEST_URI'][12:]
    doc = get_document(url)

    base_dir, filename = SeleniumBrowser.screenshot_name(doc.url)

    context = get_context(doc)
    context.update({
        'screenshot': settings.SOSSE_SCREENSHOTS_URL + '/' + base_dir + '/' + filename,
        'other_links': [{
            'href': reverse('www', args=[url]),
            'text': 'Cached page',
        }, {
            'href': reverse('words', args=[url]),
            'text': 'Words weight',
        }],
        'links': doc.links_to.filter(screen_pos__isnull=False).order_by('link_no'),
        'screens': range(doc.screenshot_count or 0)
    })
    return render(request, 'se/screenshot.html', context)
