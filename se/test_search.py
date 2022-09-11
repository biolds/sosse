
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.test import TestCase
from django.utils import timezone
from requests import HTTPError

from .browser import RequestBrowser, Page
from .forms import SearchForm
from .models import Document, Link
from .search import get_documents


class SearchTest(TestCase):
    def setUp(self):
        self.root = Document.objects.create(url='http://127.0.0.1/',
                                            normalized_url='http://127.0.0.1/',
                                            content='Hello world',
                                            normalized_content='Hello world',
                                            title='Root',
                                            normalized_title='Root',
                                            crawl_last=timezone.now())
        self.page = Document.objects.create(url='http://127.0.0.1/page1',
                                            normalized_url='http://127.0.0.1/page1',
                                            content='Page1',
                                            normalized_content='Page1',
                                            title='Page1',
                                            normalized_title='Page1',
                                            crawl_last=timezone.now())
        self.link = Link.objects.create(doc_from=self.root,
                                        doc_to=self.page,
                                        text='link text',
                                        pos=0,
                                        link_no=0)

        self.extern_link = Link.objects.create(doc_from=self.page,
                                            text='extern site',
                                            pos=0,
                                            link_no=0,
                                            extern_url='http://perdu.com')

    def tearDown(self):
        self.root.delete()
        self.page.delete()

    def _search_docs(self, params):
        request = WSGIRequest({
            'REQUEST_METHOD': 'GET',
            'QUERY_STRING': params,
            'wsgi.input': ''
        })
        form = SearchForm(request.GET)
        self.assertTrue(form.is_valid())
        return get_documents(request, form)[1]

    def test_001_q_search(self):
        docs = self._search_docs('q=hello')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_002_doc_contains(self):
        docs = self._search_docs('ft1=inc&ff1=doc&fo1=contain&fv1=hello')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_003_content_contains(self):
        docs = self._search_docs('ft1=inc&ff1=content&fo1=contain&fv1=hello')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_004_url_contains(self):
        docs = self._search_docs('ft1=inc&ff1=url&fo1=contain&fv1=page')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_005_title_contains(self):
        docs = self._search_docs('ft1=inc&ff1=title&fo1=contain&fv1=root')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_006_links_to_url_contains(self):
        docs = self._search_docs('ft1=inc&ff1=lto_url&fo1=contain&fv1=page')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_007_links_to_text_contains(self):
        docs = self._search_docs('ft1=inc&ff1=lto_txt&fo1=contain&fv1=extern')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_010_linked_by_url_contains(self):
        docs = self._search_docs('ft1=inc&ff1=lby_url&fo1=regexp&fv1=^http://127.0.0.1/$')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_011_linked_by_text_contains(self):
        docs = self._search_docs('ft1=inc&ff1=lby_txt&fo1=contain&fv1=text')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_012_regexp(self):
        docs = self._search_docs('ft1=inc&ff1=doc&fo1=regexp&fv1=hel.*')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

        docs = self._search_docs('ft1=inc&ff1=doc&fo1=regexp&fv1=hel[^l]')
        self.assertEqual(docs.count(), 0)

    def test_013_equal(self):
        docs = self._search_docs('ft1=inc&ff1=doc&fo1=equal&fv1=hello world')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

        docs = self._search_docs('ft1=inc&ff1=doc&fo1=equal&fv1=hello')
        self.assertEqual(docs.count(), 0)

    def test_014_case(self):
        docs = self._search_docs('ft1=inc&ff1=doc&fo1=contain&fv1=Hello&fc1=on')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

        docs = self._search_docs('ft1=inc&ff1=doc&fo1=contain&fv1=hello&fc1=on')
        self.assertEqual(docs.count(), 0)

    def test_015_exclude(self):
        docs = self._search_docs('ft1=exc&ff1=doc&fo1=contain&fv1=Hello')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

