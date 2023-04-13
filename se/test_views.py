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

from datetime import datetime

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.test.client import Client

from se.atom import atom
from se.models import CrawlerStats, CrawlPolicy, Document, DomainSetting
from se.screenshot import screenshot
from se.stats import stats
from se.views import about, history, opensearch, prefs, search, search_redirect, word_stats
from se.words import words
from se.www import www


class ViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = User.objects.create(username='admin', is_superuser=True, is_staff=True)
        cls.user.set_password('admin')
        cls.user.save()
        cls.crawl_policy = CrawlPolicy.create_default()
        cls.crawl_policy.default_browse_mode = DomainSetting.BROWSE_SELENIUM
        cls.crawl_policy.take_screenshots = True
        cls.crawl_policy.save()
        cls.doc = Document.objects.create(url='http://127.0.0.1:8000/')
        Document.crawl(0)
        CrawlerStats.create(datetime.now())

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.doc.delete()
        cls.crawl_policy.delete()

    def setUp(self):
        self.factory = RequestFactory()

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
                            ('/www/http://127.0.0.1:8000/', www),
                            ('/words/http://127.0.0.1:8000/', words),
                            ('/screenshot/http://127.0.0.1:8000/', screenshot)):
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
        c = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self.assertTrue(c.login(username='admin', password='admin'))

        for url in ('/admin/', '/admin/se/document/queue/', '/admin/se/document/crawl_status/',
                    '/admin/se/crawlpolicy/', '/admin/se/crawlpolicy/%s/change/' % self.crawl_policy.id,
                    '/admin/se/document/', '/admin/se/document/%s/change/' % self.doc.id,
                    '/admin/se/domainsetting/', '/admin/se/cookie/', '/admin/se/excludedurl/', '/admin/se/searchengine/'):
            response = c.get(url)
            self.assertEqual(response.status_code, 200, '%s / %s' % (url, response))
