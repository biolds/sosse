# Copyright 2022-2024 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

from urllib.parse import quote
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TransactionTestCase
from django.test.client import Client
from django.utils import timezone

from se.atom import atom
from se.browser import ChromiumBrowser, FirefoxBrowser
from se.cached import cache_redirect
from se.document import Document
from se.html import html, html_excluded
from se.models import CrawlerStats, CrawlPolicy, DomainSetting
from se.online import online_check
from se.screenshot import screenshot, screenshot_full
from se.views import about, history, opensearch, prefs, search, search_redirect, stats, word_stats
from se.words import words
from se.www import www


CRAWL_URL = 'http://127.0.0.1:8000/cookies'


class ViewsTest:
    def setUp(self):
        self.user = User.objects.create(username='admin', is_superuser=True, is_staff=True)
        self.user.set_password('admin')
        self.user.save()
        self.crawl_policy = CrawlPolicy.create_default()
        self.crawl_policy.default_browse_mode = self.BROWSER
        self.crawl_policy.take_screenshots = True
        self.crawl_policy.screenshot_format = Document.SCREENSHOT_PNG
        self.crawl_policy.save()
        self.doc = Document.objects.create(url=CRAWL_URL)
        Document.crawl(0)
        CrawlerStats.create(timezone.now())

        self.factory = RequestFactory()
        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self.assertTrue(self.client.login(username='admin', password='admin'))

    @classmethod
    def tearDownClass(cls):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()
        try:
            os.unlink(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1,3A8000/cookies_98ba5952821ca60c491fa81c6214e26f.html')
        except OSError:
            pass
        try:
            os.rmdir(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/127.0.0.1,3A8000/')
            os.rmdir(settings.SOSSE_HTML_SNAPSHOT_DIR + 'http,3A/')
        except OSError:
            pass

    def _request_from_factory(self, url):
        request = self.factory.get(url)
        request.META['REQUEST_URI'] = url
        request.META['REQUEST_SCHEME'] = 'http'
        request.META['HTTP_HOST'] = '127.0.0.1'
        request.user = self.user
        return request

    def test_views(self):
        for (url, view, args) in (('/?q=page', search, tuple()),
                                  ('/about/', about, tuple()),
                                  ('/prefs/', prefs, tuple()),
                                  ('/stats/', stats, tuple()),
                                  ('/history/', history, tuple()),
                                  ('/?q=page', search, tuple()),
                                  ('/s/?q=page', search_redirect, tuple()),
                                  ('/atom/?q=page', atom, tuple()),
                                  ('/atom/?q=page&cached=1', atom, tuple()),
                                  ('/word_stats/?q=page', word_stats, tuple()),
                                  ('/opensearch.xml', opensearch, tuple()),
                                  ('/html/' + CRAWL_URL, html, tuple()),
                                  ('/www/' + CRAWL_URL, www, tuple()),
                                  ('/www/http://unknown/', www, tuple()),
                                  ('/words/' + CRAWL_URL, words, tuple()),
                                  ('/screenshot/' + CRAWL_URL, screenshot, tuple()),
                                  ('/screenshot_full/' + CRAWL_URL, screenshot_full, tuple()),
                                  ('/online_check/' + CRAWL_URL, online_check, tuple()),
                                  (f'/html_excluded/{self.crawl_policy.id}/url', html_excluded, (self.crawl_policy.id, 'url'))):

            request = self._request_from_factory(url)
            try:
                response = view(request, *args)
            except:  # noqa
                raise Exception('Failed on %s' % url)
            self.assertEqual(response.status_code, 200, f'{url}\n{response.content}\n{response.headers}')

    def test_new_urls(self):
        from sosse.urls import urlpatterns
        self.assertEqual(len(urlpatterns), 25)

    def test_cache_redirect(self):
        request = self._request_from_factory('/cache/' + CRAWL_URL)
        response = cache_redirect(request)
        self.assertEqual(response.status_code, 302, response)
        self.assertEqual(response.url, '/screenshot/' + CRAWL_URL, response)

    def test_admin_views(self):
        for url in ('/admin/', '/admin/se/document/queue/', '/admin/se/document/crawl_status/', '/admin/se/document/crawl_status_content/',
                    '/admin/se/crawlpolicy/', '/admin/se/crawlpolicy/%s/change/' % self.crawl_policy.id,
                    '/admin/se/document/', '/admin/se/document/?queued=new', '/admin/se/document/?queued=pending', '/admin/se/document/?queued=recurring',
                    '/admin/se/document/?has_error=yes', '/admin/se/document/?has_error=no',
                    '/admin/se/document/%s/change/' % self.doc.id,
                    '/admin/se/domainsetting/', '/admin/se/domainsetting/%s/change/' % DomainSetting.get_from_url(CRAWL_URL).id,
                    '/admin/se/cookie/', '/admin/se/cookie/?q=%s' % quote(CRAWL_URL),
                    '/admin/se/excludedurl/', '/admin/se/searchengine/', '/admin/se/searchengine/?conflict=yes',
                    '/admin/se/htmlasset/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, '%s / %s' % (url, response))

    def test_admin_doc_actions(self):
        for action in ('remove_from_crawl_queue', 'convert_to_jpg'):
            response = self.client.post('/admin/se/document/%s/do_action/' % self.doc.id, {'action': action})
            self.assertEqual(response.status_code, 302, '%s / %s' % (action, response))
            self.assertEqual(response.url, '/admin/se/document/%s/change/' % self.doc.id, '%s / %s' % (action, response))

        response = self.client.post('/admin/se/document/%s/do_action/' % self.doc.id, {'action': 'crawl_now'})
        self.assertEqual(response.status_code, 302, '%s / %s' % (action, response))
        self.assertEqual(response.url, '/admin/se/document/crawl_status/', '%s / %s' % (action, response))

    def test_admin_crawl_status_actions(self):
        for action in ('pause', 'resume'):
            response = self.client.post('/admin/se/document/crawl_status/', {action: "1"})
            self.assertEqual(response.status_code, 200, '%s / %s' % (action, response))

    def test_admin_add_crawl(self):
        response = self.client.post('/admin/se/document/queue_confirm/', {'url': CRAWL_URL})
        self.assertEqual(response.status_code, 200, response)

        response = self.client.post('/admin/se/document/queue_confirm/', {'url': CRAWL_URL, 'action': 'Confirm'})
        self.assertEqual(response.status_code, 302, response)


class ChromiumViewTest(ViewsTest, TransactionTestCase):
    BROWSER = DomainSetting.BROWSE_CHROMIUM


class FirefoxViewTest(ViewsTest, TransactionTestCase):
    BROWSER = DomainSetting.BROWSE_FIREFOX
