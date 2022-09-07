from unittest import mock

from django.test import TestCase
from requests import HTTPError

from .browser import RequestBrowser, Page
from .models import Document, DomainSetting, Link, UrlPolicy


class BrowserMock:
    def __init__(self, web):
        self.web = {
            'http://127.0.0.1/robots.txt': HTTPError(),
            'http://127.0.0.1/favicon.ico': HTTPError()
        }
        self.web.update(web)

    def __call__(self, url, raw=False, check_status=False):
        content = self.web[url]
        if isinstance(content, HTTPError):
            raise content
        return Page(url, content, {}, BrowserMock)


class CrawlerTest(TestCase):
    DEFAULT_GETS = [
        mock.call('http://127.0.0.1/robots.txt', check_status=True),
        mock.call('http://127.0.0.1/'),
        mock.call('http://127.0.0.1/favicon.ico', raw=True, check_status=True),
    ]

    def setUp(self):
        RequestBrowser.init()
        self.root_policy = UrlPolicy.objects.create(url_prefix='',
                                                    no_crawl=True)
        self.url_policy = UrlPolicy.objects.create(url_prefix='http://127.0.0.1/',
                                                   no_crawl=False,
                                                   default_browse_mode=DomainSetting.BROWSE_REQUESTS)

    def tearDown(self):
        self.root_policy.delete()
        self.url_policy.delete()

    def _crawl(self):
        Document.queue('http://127.0.0.1/', None)
        while Document.crawl(0):
            pass

    @mock.patch('se.browser.RequestBrowser.get')
    def test_001_hello_world(self, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({'http://127.0.0.1/': 'Hello world'})
        self._crawl()
        self.assertTrue(RequestBrowser.call_args_list == self.DEFAULT_GETS,
                        RequestBrowser.call_args_list)

        domain_setting = DomainSetting.objects.get()
        self.assertEqual(domain_setting.url_policy, self.url_policy)
        self.assertEqual(domain_setting.browse_mode, DomainSetting.BROWSE_REQUESTS)
        self.assertEqual(domain_setting.domain, '127.0.0.1')
        self.assertEqual(domain_setting.robots_status, DomainSetting.ROBOTS_EMPTY)

        self.assertEqual(Document.objects.count(), 1)
        doc = Document.objects.get()
        self.assertEqual(doc.url, 'http://127.0.0.1/')
        self.assertEqual(doc.content, 'Hello world')
        self.assertEqual(doc.crawl_depth, None)

        self.assertEqual(Link.objects.count(), 0)

    @mock.patch('se.browser.RequestBrowser.get')
    def test_002_link_follow(self, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({
            'http://127.0.0.1/': 'Root <a href="/page1/">Link1</a>',
            'http://127.0.0.1/page1/': 'Page1'
        })
        self._crawl()
        self.assertTrue(RequestBrowser.call_args_list == self.DEFAULT_GETS + [
                mock.call('http://127.0.0.1/page1/'),
            ],
            RequestBrowser.call_args_list)

        self.assertEqual(Document.objects.count(), 2)
        docs = Document.objects.order_by('id')
        self.assertEqual(docs[0].url, 'http://127.0.0.1/')
        self.assertEqual(docs[0].content, 'Root Link1')
        self.assertEqual(docs[0].crawl_depth, None)
        self.assertEqual(docs[1].url, 'http://127.0.0.1/page1/')
        self.assertEqual(docs[1].content, 'Page1')
        self.assertEqual(docs[1].crawl_depth, None)

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, docs[0])
        self.assertEqual(link.doc_to, docs[1])
        self.assertEqual(link.text, 'Link1')
        self.assertEqual(link.pos, 5)
        self.assertEqual(link.link_no, 0)

    @mock.patch('se.browser.RequestBrowser.get')
    def test_003_crawl_depth(self, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({
            'http://127.0.0.1/': 'Root <a href="/page1/">Link1</a>',
            'http://127.0.0.1/page1/': 'Page1 <a href="/page2/">Link2</a>',
            'http://127.0.0.1/page2/': 'Page2',
        })
        self.url_policy.crawl_depth = 2
        self.url_policy.save()
        self._crawl()
        self.assertTrue(RequestBrowser.call_args_list == self.DEFAULT_GETS + [
                mock.call('http://127.0.0.1/page1/'),
            ],
            RequestBrowser.call_args_list)

        self.assertEqual(Document.objects.count(), 2)
        docs = Document.objects.order_by('id')
        self.assertEqual(docs[0].url, 'http://127.0.0.1/')
        self.assertEqual(docs[0].content, 'Root Link1')
        self.assertEqual(docs[0].crawl_depth, 1)
        self.assertEqual(docs[1].url, 'http://127.0.0.1/page1/')
        self.assertEqual(docs[1].content, 'Page1 Link2')
        self.assertEqual(docs[1].crawl_depth, 2)

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, docs[0])
        self.assertEqual(link.doc_to, docs[1])
        self.assertEqual(link.text, 'Link1')
        self.assertEqual(link.pos, 5)
        self.assertEqual(link.link_no, 0)

    @mock.patch('se.browser.RequestBrowser.get')
    def test_004_no_crawl(self, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({
            'http://127.0.0.1/': 'Root <a href="/page1/">Link1</a>',
            'http://127.0.0.1/page1/': 'Page1',
        })
        UrlPolicy.objects.create(url_prefix='http://127.0.0.1/page1/', no_crawl=True)
        self._crawl()
        self.assertTrue(RequestBrowser.call_args_list == self.DEFAULT_GETS,
                       RequestBrowser.call_args_list)

        self.assertEqual(Document.objects.count(), 1)
        docs = Document.objects.order_by('id')
        self.assertEqual(docs[0].url, 'http://127.0.0.1/')
        self.assertEqual(docs[0].content, 'Root Link1')
        self.assertEqual(docs[0].crawl_depth, None)

        self.assertEqual(Link.objects.count(), 0)

    @mock.patch('se.browser.RequestBrowser.get')
    def test_005_extern_links(self, RequestBrowser):
        RequestBrowser.side_effect = BrowserMock({
            'http://127.0.0.1/': 'Root <a href="/page1/">Link1</a>',
            'http://127.0.0.1/page1/': 'Page1',
        })
        self.url_policy.keep_extern_links = True
        self.url_policy.save()
        UrlPolicy.objects.create(url_prefix='http://127.0.0.1/page1/', no_crawl=True)
        self._crawl()
        self.assertTrue(RequestBrowser.call_args_list == self.DEFAULT_GETS,
                       RequestBrowser.call_args_list)

        self.assertEqual(Document.objects.count(), 1)
        docs = Document.objects.order_by('id')
        self.assertEqual(docs[0].url, 'http://127.0.0.1/')
        self.assertEqual(docs[0].content, 'Root Link1')
        self.assertEqual(docs[0].crawl_depth, None)

        self.assertEqual(Link.objects.count(), 1)
        link = Link.objects.get()
        self.assertEqual(link.doc_from, docs[0])
        self.assertEqual(link.doc_to, None)
        self.assertEqual(link.text, 'Link1')
        self.assertEqual(link.pos, 5)
        self.assertEqual(link.link_no, 0)
        self.assertEqual(link.extern_url, 'http://127.0.0.1/page1/')
