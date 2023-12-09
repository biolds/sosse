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

from django.test import TransactionTestCase

from .browser import ChromiumBrowser, FirefoxBrowser, Page
from .document import Document
from .models import CrawlPolicy, Link
from .utils import http_date_format, http_date_parser
from .www import get_content


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
    'expected_output': 'http://test.com/%61%62%63/',
}, {
    'descr': b'relative link',
    'link': b'http://test.com/test/../abc/',
    'expected_output': 'http://test.com/abc/'
}, {
    'descr': b'percent-encoded relative link',
    'link': b'http://test.com/test/%2e%2e/abc/',
    'expected_output': 'http://test.com/test/%2e%2e/abc/'
}, {
    'descr': b'space link',
    'link': b'http://test.com/test/a b c/',
    'expected_output': 'http://test.com/test/a%20b%20c/',
}, {
    'descr': b'percent-encoded space link',
    'link': b'http://test.com/test/a%20b%20c/',
}, {
    'descr': b'reserved characters link',
    'link': b'http://test.com/, &/',
    'expected_output': 'http://test.com/,%20&/',
}, {
    'descr': b'percent-encoded slash link',
    'link': b'http://test.com/test/a%2fb/',
    'expected_output': 'http://test.com/test/a%2fb/',
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


ATOM_FEED = b'''
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Feed title</title>
  <description>Feed description</description>
  <link href="http://192.168.120.5/"/>
  <updated>2023-08-29T10:13:27.161859+00:00</updated>
  <id>urn:uuid:02439bf8-bb91-83a1-12e2-f71bb60a0b73</id>
  <icon>http://192.168.120.5/static/logo.svg</icon>
  <entry>
    <title>Entry one</title>
    <link href="http://192.168.120.5/entry-one"/>
    <id>urn:uuid:029c6cf9-f277-f085-f2e0-f670aab4f7d0</id>
    <updated>2023-08-29T10:13:27.161859+00:00</updated>
    <summary>Summary one</summary>
  </entry>
  <entry>
    <title>Entry two</title>
    <link href="http://192.168.120.5/entry-two"/>
    <id>urn:uuid:ad96514e-0246-0892-8e07-0b3d84ced537</id>
    <updated>2023-08-29T10:09:08.250034+00:00</updated>
    <summary>Summary two</summary>
  </entry>
</feed>
'''


ATOM_FEED_WITH_HEADER = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ATOM_FEED


RSS_FEED = b'''
<rss version="2.0">
  <channel>
    <title>Feed title</title>
    <link>http://192.168.120.5/</link>
    <description>Feed description</description>
    <language>en</language>
    <item>
      <title>Entry one</title>
      <link>http://192.168.120.5/entry-one</link>
      <description>Summary one</description>
      <author>test@exemple.org</author>
      <pubDate>Wed, 29 Aug 2023 10:13:27 GMT</pubDate>
    </item>
    <item>
      <title>Entry two</title>
      <link>http://192.168.120.5/entry-two</link>
      <description>Summary two</description>
      <author>test@exemple.org</author>
      <pubDate>Wed, 29 Aug 2023 10:09:08 GMT</pubDate>
    </item>
  </channel>
</rss>
'''


class PageTest(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = CrawlPolicy.create_default()
        cls.policy.snapshot_html = False
        cls.policy.save()

    @classmethod
    def tearDownClass(cls):
        ChromiumBrowser.destroy()
        FirefoxBrowser.destroy()
        cls.policy.delete()

    def test_10_beautifulsoup(self):
        page = Page('http://127.0.0.1/', FAKE_PAGE, None)
        links = list(page.get_links(True))

        self.assertEqual(len(links), len(LINKS))
        for no, link in enumerate(links):
            expected = LINKS[no].get('expected_output', LINKS[no]['link'].decode('utf-8'))
            self.assertEqual(link, expected, '%s failed' % LINKS[no]['descr'])

    NAV_HTML = b'<html><body><header>header</header><nav>nav<a href="link">link</a></nav>text<footer>footer</footer></body></html>'

    def test_20_no_nav_element(self):
        page = Page('http://test/', self.NAV_HTML, None)
        doc = Document.objects.create(url=page.url)
        doc.index(page, self.policy)
        self.assertEqual(doc.content, 'text')
        links = Link.objects.order_by('id')
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].in_nav)

        www_content = get_content(doc)
        self.assertEqual(www_content, ' <a href="/www/http://test/link">link</a>text<br/>')

    def test_30_nav_element(self):
        page = Page('http://test/', self.NAV_HTML, None)
        doc = Document.objects.create(url=page.url)
        self.policy.remove_nav_elements = CrawlPolicy.REMOVE_NAV_NO
        doc.index(page, self.policy)
        self.assertEqual(doc.content, 'header nav link text footer')

        links = Link.objects.order_by('id')
        self.assertEqual(len(links), 1)
        self.assertFalse(links[0].in_nav)

        www_content = get_content(doc)
        self.assertEqual(www_content, 'header nav  <a href="/www/http://test/link">link</a> text footer<br/>')

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

    def test_60_no_comment(self):
        page = Page('http://test/', b'<html><body><!-- nothing -->text</body></html>', None)
        doc = Document(url=page.url)
        doc.index(page, self.policy)
        self.assertEqual(doc.content, 'text')

    def test_70_feeds(self):
        for feed in (ATOM_FEED, ATOM_FEED_WITH_HEADER, RSS_FEED):
            page = Page('http://test/', feed, None)
            doc = Document.objects.create(url=page.url)
            doc.index(page, self.policy)

            self.assertEqual(Document.objects.count(), 4)
            self.assertEqual(doc.url, page.url)
            self.assertEqual(doc.title, 'Feed title')
            self.assertEqual(doc.content, 'Feed title\nFeed description\n08/29/2023 10:13 a.m. Entry one\n08/29/2023 10:09 a.m. Entry two\n')
            self.assertEqual(doc.mimetype, 'text/html')

            links = Link.objects.order_by('id')
            self.assertEqual(links.count(), 3)

            self.assertEqual(links[0].text, 'Feed title')
            self.assertEqual(links[0].doc_to.url, 'http://192.168.120.5/')
            self.assertEqual(links[1].text, 'Entry one')
            self.assertEqual(links[1].doc_to.url, 'http://192.168.120.5/entry-one')
            self.assertEqual(links[2].text, 'Entry two')
            self.assertEqual(links[2].doc_to.url, 'http://192.168.120.5/entry-two')

            Document.objects.all().delete()
