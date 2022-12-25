from django.conf import settings
from django.shortcuts import render, reverse

from .cached import get_document, get_context
from .login import login_required


@login_required
def words(request, url):
    url = request.META['REQUEST_URI'][7:]
    doc = get_document(url)
    context = get_context(doc)
    words = []
    for w in doc.vector.split():
        word, weights = w.split(':', 1)
        word = word.strip("'")
        words.append((word, weights))

    context.update({
        'other_links': [{
            'href': reverse('www', args=[url]),
            'text': 'Cached page',
        }, {
            'href': reverse('screenshot', args=[url]),
            'text': 'Screenshot'
        }],
        'words': words,
        'lang': doc.lang_flag(True)
    })
    return render(request, 'se/words.html', context)

