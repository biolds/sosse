# Copyright 2025 Laurent Defert
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


from django.template.response import SimpleTemplateResponse
from django.test import TransactionTestCase

from .add_to_queue import AddToQueueConfirmationView
from .crawl_policy import CrawlPolicy
from .document import Document
from .test_views_mixin import ViewsTestMixin


class FakeAdminSite:
    def each_context(self, request):
        return {}


class AddToQueueTest(ViewsTestMixin, TransactionTestCase):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        CrawlPolicy.objects.create(url_regex="https://alternative-policy.com/", recursion=CrawlPolicy.CRAWL_ALL)

    def _request(self, params):
        request = self._request_from_factory("/admin/se/document/queue_confirm/", self.admin_user, "post", params)
        response = AddToQueueConfirmationView.as_view(admin_site=FakeAdminSite())(request)
        if isinstance(response, SimpleTemplateResponse):
            response.render()
        return response

    def test_check_one_url(self):
        urls = "https://example-1.com"
        response = self._request({"urls": urls})
        self.assertEqual(response.status_code, 200)

    def test_check_multi_urls(self):
        urls = "https://example-1.com\nhttps://example-2.com"
        response = self._request({"urls": urls})
        self.assertEqual(response.status_code, 200)

    def test_check_multi_urls_multi_policy(self):
        urls = "https://example-1.com\nhttps://alternative_policy.com/"
        response = self._request({"urls": urls})
        self.assertEqual(response.status_code, 200)

    def test_confirm_one_url(self):
        urls = "https://example-1.com"
        response = self._request({"urls": urls, "action": "Confirm"})
        self.assertEqual(response.status_code, 302)

        docs = Document.objects.order_by("url")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].url, "https://example-1.com/")

    def test_confirm_multi_urls(self):
        urls = "https://example-1.com\nhttps://example-2.com"
        response = self._request({"urls": urls, "action": "Confirm"})
        self.assertEqual(response.status_code, 302)

        docs = Document.objects.order_by("url")
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0].url, "https://example-1.com/")
        self.assertEqual(docs[1].url, "https://example-2.com/")

    def test_confirm_failure(self):
        urls = "https://example.com\nhtt://example2.com"
        response = self._request({"urls": urls, "action": "Confirm"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid URL:\nLine 2:", response.content.decode())
