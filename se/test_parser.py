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

# This file checks url conversion (percent encoding, punycode, spaces ...) and consistencies
# across classes and external libraries

from datetime import datetime, timezone

from django.test import TestCase

from .browser import Browser, Page
from .document import Document
from .models import CrawlPolicy
from .utils import http_date_format, http_date_parser


LINKS = ({
    'descr': b'regular link',
    'link': b'http://test.com/',
}, {
    'descr': b'percent-encoded utf8 link',
    'link': b'http://test.com/%F0%9F%90%88/',
}, {
    'descr': b'utf8 link',
    'link': 'http://test.com/🐈/'.encode('utf-8'),
    'expected_output': 'http://test.com/%F0%9F%90%88/',
}, {
    'descr': b'utf8 domain',
    'link': 'http://🐈.com/'.encode('utf-8'),
    'expected_output': 'http://xn--zn8h.com/',
}, {
    'descr': b'punycode-encoded utf8 domain',
    'link': b'http://xn--zn8h.com/',
}, {
    'descr': b'percent-encode ascii link',
    'link': b'http://test.com/%61%62%63/',
    'expected_output': 'http://test.com/abc/',
}, {
    'descr': b'relative link',
    'link': b'http://test.com/test/../abc/',
    'expected_output': 'http://test.com/abc/'
}, {
    'descr': b'percent-encoded relative link',
    'link': b'http://test.com/test/%2e%2e/abc/',
    'expected_output': 'http://test.com/abc/'
}, {
    'descr': b'space link',
    'link': b'http://test.com/test/a b c/',
    'expected_output': 'http://test.com/test/a%20b%20c/',
}, {
    'descr': b'percent-encoded space link',
    'link': b'http://test.com/test/a%20b%20c/',
}, {
    'descr': b'special characters link',
    'link': b'http://test.com/, &/',
    'expected_output': 'http://test.com/%2C%20%26/',
}, {
    'descr': b'percent-encoded slash link',
    'link': b'http://test.com/test/a%2fb/',
    'expected_output': 'http://test.com/test/a/b/',
}, {
    'descr': b'url parameters',
    'link': b'http://test.com/?a=b',
}, {
    'descr': b'url parameters with space',
    'link': b'http://test.com/?a=a b',
    'expected_output': 'http://test.com/?a=a+b',
}, {
    'descr': b'url parameters with plus',
    'link': b'http://test.com/?a=a+b',
}, {
    'descr': b'url parameters with percents',
    'link': b'http://test.com/?a=a%20b',
    'expected_output': 'http://test.com/?a=a+b',
}, {
    'descr': b'url parameters with slash',
    'link': b'http://test.com/?a=a/b',
    'expected_output': 'http://test.com/?a=a%2Fb',
}, {
    'descr': b'url with sharp',
    'link': b'http://test.com/test#test/',
    'expected_output': 'http://test.com/test',
}, {
    'descr': b'no trailing slash hostname',
    'link': b'http://test.com',
    'expected_output': 'http://test.com/',
}, {
    'descr': b'trailing slash hostname',
    'link': b'http://test.com/',
}, {
    'descr': b'no trailing slash path',
    'link': b'http://test.com/test',
}, {
    'descr': b'trailing slash path',
    'link': b'http://test.com/test/',
})

FAKE_PAGE = b'''
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"></head>'
  <body>
    %s
  </body>
</html>
''' % b'\n'.join([b'<a href="%s">%s</a>' % (link['link'], link['descr']) for link in LINKS])


class PageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        Browser.init()
        cls.policy = CrawlPolicy.create_default()
        cls.policy.snapshot_html = False
        cls.policy.save()

    @classmethod
    def tearDownClass(cls):
        Browser.destroy()
        cls.policy.delete()

    def test_10_beautifulsoup(self):
        page = Page('http://127.0.0.1/', FAKE_PAGE, None)
        links = list(page.get_links(True))

        self.assertEqual(len(links), len(LINKS))
        for no, link in enumerate(links):
            expected = LINKS[no].get('expected_output', LINKS[no]['link'].decode('utf-8'))
            self.assertEqual(link, expected, '%s failed' % LINKS[no]['descr'])

    NAV_HTML = b'<html><body><header>header</header><nav>nav</nav>text<footer>footer</footer></body></html>'

    def test_20_no_nav_element(self):
        page = Page('http://test/', self.NAV_HTML, None)
        doc = Document(url=page.url)
        doc.index(page, self.policy)
        self.assertEqual(doc.content, 'text')

    def test_30_nav_element(self):
        page = Page('http://test/', self.NAV_HTML, None)
        doc = Document(url=page.url)
        self.policy.remove_nav_elements = CrawlPolicy.REMOVE_NAV_NO
        doc.index(page, self.policy)
        self.assertEqual(doc.content, 'header nav text footer')

    DATES = (
        ('Wed, 21 Oct 2015 07:28:00 GMT', datetime(2015, 10, 21, 7, 28, 0, tzinfo=timezone.utc)),
        ('Tue, 22 Feb 2022 22:22:22 GMT', datetime(2022, 2, 22, 22, 22, 22, tzinfo=timezone.utc))
    )

    def test_40_http_date_parse(self):
        for s, d in self.DATES:
            self.assertEqual(http_date_parser(s), d)

    def test_50_http_date_fromat(self):
        for s, d in self.DATES:
            self.assertEqual(s, http_date_format(d))
