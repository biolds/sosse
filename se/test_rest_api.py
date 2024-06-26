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

import json

from collections import namedtuple
from unittest import mock

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.test.client import Client
from django.utils import timezone

from .document import Document
from .models import CrawlerStats


now = timezone.now()
now_str = now.isoformat().replace('+00:00', 'Z')
SERIALIZED_DOC1 = {
    'content': 'Content',
    'content_hash': None,
    'crawl_dt': None,
    'crawl_first': now_str,
    'crawl_last': now_str,
    'crawl_next': None,
    'crawl_recurse': 0,
    'error': '',
    'error_hash': '',
    'favicon': None,
    'has_html_snapshot': False,
    'has_thumbnail': False,
    'hidden': False,
    'lang_iso_639_1': 'en',
    'mimetype': None,
    'normalized_content': 'content',
    'normalized_title': 'title',
    'normalized_url': 'http test',
    'redirect_url': None,
    'robotstxt_rejected': False,
    'screenshot_count': 0,
    'screenshot_format': '',
    'screenshot_size': '',
    'show_on_homepage': False,
    'title': 'Title',
    'too_many_redirects': False,
    'url': 'http://127.0.0.1/test',
    'vector': "'content':4C 'http':2A 'test':3A 'title':1A",
    'vector_lang': 'simple',
    'worker_no': None
}


SERIALIZED_CRAWLER_STATS = [{
    'doc_count': 23,
    'freq': 'M',
    'indexing_speed': 2,
    'queued_url': 24,
    't': now_str
}, {
    'doc_count': 33,
    'freq': 'D',
    'indexing_speed': 4,
    'queued_url': 34,
    't': now_str
}]


class RestAPITest:
    maxDiff = None

    def setUp(self):
        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self.user = User.objects.create(username='admin', password='admin', is_superuser=True)
        self.user.set_password('admin')
        self.user.save()
        self.client.login(username='admin', password='admin')

        self.doc1 = Document.objects.create(url='http://127.0.0.1/test',
                                            normalized_url='http test',
                                            title='Title',
                                            normalized_title='title',
                                            content='Content',
                                            normalized_content='content',
                                            crawl_first=now,
                                            crawl_last=now,
                                            lang_iso_639_1='en')
        self.doc2 = Document.objects.create(url='http://127.0.0.1/test2',
                                            normalized_url='http test2',
                                            title='Title2',
                                            normalized_title='title2',
                                            content='Other Content2',
                                            normalized_content='other content2',
                                            crawl_first=now,
                                            crawl_last=now,
                                            lang_iso_639_1='en')

        self.crawler_stat1 = CrawlerStats.objects.create(t=now,
                                                         doc_count=23,
                                                         queued_url=24,
                                                         indexing_speed=2,
                                                         freq='M')
        self.crawler_stat2 = CrawlerStats.objects.create(t=now,
                                                         doc_count=33,
                                                         queued_url=34,
                                                         indexing_speed=4,
                                                         freq='D')


class APIQueryTest(RestAPITest, TransactionTestCase):
    def test_document_list(self):
        response = self.client.get('/api/document/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [
                SERIALIZED_DOC1 | {'id': self.doc1.id}, {
                    'content': 'Other Content2',
                    'content_hash': None,
                    'crawl_dt': None,
                    'crawl_first': now_str,
                    'crawl_last': now_str,
                    'crawl_next': None,
                    'crawl_recurse': 0,
                    'error': '',
                    'error_hash': '',
                    'favicon': None,
                    'has_html_snapshot': False,
                    'has_thumbnail': False,
                    'hidden': False,
                    'id': self.doc2.id,
                    'lang_iso_639_1': 'en',
                    'mimetype': None,
                    'normalized_content': 'other content2',
                    'normalized_title': 'title2',
                    'normalized_url': 'http test2',
                    'redirect_url': None,
                    'robotstxt_rejected': False,
                    'screenshot_count': 0,
                    'screenshot_format': '',
                    'screenshot_size': '',
                    'show_on_homepage': False,
                    'title': 'Title2',
                    'too_many_redirects': False,
                    'url': 'http://127.0.0.1/test2',
                    'vector': "'content2':5C 'http':2A 'other':4C 'test2':3A 'title2':1A",
                    'vector_lang': 'simple',
                    'worker_no': None
                }
            ]
        })

    def test_document_detail(self):
        response = self.client.get(f'/api/document/{self.doc1.id}/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), SERIALIZED_DOC1 | {'id': self.doc1.id})

    def test_stats_list(self):
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [
                SERIALIZED_CRAWLER_STATS[0] | {'id': self.crawler_stat1.id},
                SERIALIZED_CRAWLER_STATS[1] | {'id': self.crawler_stat2.id}
            ]
        })

    def test_stats_detail(self):
        response = self.client.get(f'/api/stats/{self.crawler_stat1.id}/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), SERIALIZED_CRAWLER_STATS[0] | {'id': self.crawler_stat1.id})

    def test_stats_list_filter(self):
        response = self.client.get('/api/stats/?freq=M')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                SERIALIZED_CRAWLER_STATS[0] | {'id': self.crawler_stat1.id},
            ]
        })

    @mock.patch('os.statvfs')
    def test_hdd_stats(self, statvfs):
        fakevfs = namedtuple('fakevfs', ['f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail', 'f_files', 'f_ffree', 'f_favail', 'f_flag', 'f_namemax'])
        statvfs.side_effect = lambda x: fakevfs(f_bsize=4096, f_frsize=4096, f_blocks=51081736, f_bfree=30397904, f_bavail=27784887, f_files=13049856, f_ffree=11610989, f_favail=11610989, f_flag=4096, f_namemax=255)
        response = self.client.get('/api/hdd_stats/')
        self.assertEqual(response.status_code, 200, response.content)

        content = json.loads(response.content)
        self.assertEqual(json.loads(response.content), {
            'db': content['db'],
            'free': 113806897152,
            'html': content['html'],
            'other': content['other'],
            'screenshots': content['screenshots']
        })

    def test_lang_stats(self):
        response = self.client.get('/api/lang_stats/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), [{'doc_count': 2, 'lang': 'En 🇬🇧'}])

    def test_search(self):
        response = self.client.post('/api/search/', {
            'query': 'content'
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'doc_id': self.doc1.id,
                'score': 0.12158542,
                'title': 'Title',
                'url': 'http://127.0.0.1/test'
            }]
        })

    def test_search_has_params(self):
        response = self.client.post('/api/search/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {
            'non_field_errors': ['At least "query" or "adv_params" field must be provided.']
        })

    def test_search_title(self):
        response = self.client.post('/api/search/', {
            'adv_params': [{
                'field': 'content',
                'term': 'Content2'
            }]
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'doc_id': self.doc2.id,
                'score': None,
                'title': 'Title2',
                'url': 'http://127.0.0.1/test2'
            }]
        })

    def test_search_hidden(self):
        self.doc2.hidden = True
        self.doc2.save()

        response = self.client.post('/api/search/', {'query': 'http'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'doc_id': self.doc1.id,
                'score': 0.6079271,
                'title': 'Title',
                'url': 'http://127.0.0.1/test'
            }]
        })

    def test_search_hidden_included(self):
        self.doc2.hidden = True
        self.doc2.save()

        response = self.client.post('/api/search/', {'query': 'http', 'include_hidden': True})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(json.loads(response.content), {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'doc_id': self.doc1.id,
                'url': 'http://127.0.0.1/test',
                'title': 'Title',
                'score': 0.6079271
            }, {
                'doc_id': self.doc2.id,
                'url': 'http://127.0.0.1/test2',
                'title': 'Title2',
                'score': 0.6079271
            }]
        })
