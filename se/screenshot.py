from django.conf import settings
from django.shortcuts import render, reverse

from .browser import SeleniumBrowser
from .cached import get_document, get_context


def screenshot(request, url):
    doc = get_document(url)

    context = get_context(doc)
    base_dir, filename = SeleniumBrowser.screenshot_name(doc.url)
    context['screenshot'] = settings.OSSE_SCREENSHOTS_URL + '/' + base_dir + '/' + filename
    context['other_link'] = {
        'href': reverse('www', args=[url]),
        'text': 'Cached page'
    }
    return render(request, 'se/screenshot.html', context)
