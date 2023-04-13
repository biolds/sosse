# Copyright 2022-2023 Laurent Defert
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

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.test.client import Client
from django.utils import timezone

from se.atom import atom
from se.models import CrawlerStats, CrawlPolicy, Document, DomainSetting
from se.screenshot import screenshot
from se.stats import stats
from se.views import about, history, opensearch, prefs, search, search_redirect, word_stats
from se.words import words
from se.www import www


CRAWL_URL = 'http://127.0.0.1:8000/'


class ViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = User.objects.create(username='admin', is_superuser=True, is_staff=True)
        cls.user.set_password('admin')
        cls.user.save()
        cls.crawl_policy = CrawlPolicy.create_default()
        cls.crawl_policy.default_browse_mode = DomainSetting.BROWSE_SELENIUM
        cls.crawl_policy.take_screenshots = True
        cls.crawl_policy.screenshot_format = Document.SCREENSHOT_PNG
        cls.crawl_policy.save()
        cls.doc = Document.objects.create(url=CRAWL_URL)
        Document.crawl(0)
        CrawlerStats.create(timezone.now())

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.doc.delete()
        cls.crawl_policy.delete()

    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self.assertTrue(self.client.login(username='admin', password='admin'))

    def test_views(self):
        for (url, view) in (('/?q=page', search),
                            ('/about/', about),
                            ('/prefs/', prefs),
                            ('/stats/', stats),
                            ('/history/', history),
                            ('/?q=page', search),
                            ('/s/?q=page', search_redirect),
                            ('/atom/?q=page', atom),
                            ('/atom/?q=page&cached=1', atom),
                            ('/word_stats/?q=page', word_stats),
                            ('/opensearch.xml', opensearch),
                            ('/www/' + CRAWL_URL, www),
                            ('/words/' + CRAWL_URL, words),
                            ('/screenshot/' + CRAWL_URL, screenshot)):
            request = self.factory.get(url)
            request.META['REQUEST_URI'] = url
            request.META['REQUEST_SCHEME'] = 'http'
            request.META['HTTP_HOST'] = '127.0.0.1'
            request.user = self.user
            try:
                response = view(request)
            except:  # noqa
                raise Exception('Failed on %s' % url)
            self.assertEqual(response.status_code, 200, url)

    def test_admin_views(self):
        for url in ('/admin/', '/admin/se/document/queue/', '/admin/se/document/crawl_status/',
                    '/admin/se/crawlpolicy/', '/admin/se/crawlpolicy/%s/change/' % self.crawl_policy.id,
                    '/admin/se/document/', '/admin/se/document/?is_queued=yes', '/admin/se/document/?is_queued=no',
                    '/admin/se/document/?has_error=yes', '/admin/se/document/?has_error=no',
                    '/admin/se/document/%s/change/' % self.doc.id,
                    '/admin/se/domainsetting/', '/admin/se/cookie/', '/admin/se/excludedurl/', '/admin/se/searchengine/'):
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

    def test_admin_crawl(self):
        response = self.client.post('/admin/se/document/queue_confirm/', {'url': CRAWL_URL})
        self.assertEqual(response.status_code, 200, response)

        response = self.client.post('/admin/se/document/queue_confirm/', {'url': CRAWL_URL, 'action': 'Confirm'})
        self.assertEqual(response.status_code, 302, response)
