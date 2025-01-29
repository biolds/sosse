# Copyright 2022-2025 Laurent Defert
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

from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .crawl_policy import CrawlPolicy
from .document import Document
from .models import Link
from .page import Page
from .utils import http_date_format, http_date_parser
from .www import WWWView

LINKS = (
    {
        "descr": "regular link",
        "link": "http://test.com/",
    },
    {
        "descr": "percent-encoded utf8 link",
        "link": "http://test.com/%F0%9F%90%88/",
    },
    {
        "descr": "utf8 link",
        "link": "http://test.com/🐈/",
        "expected_output": "http://test.com/%F0%9F%90%88/",
    },
    {
        "descr": "utf8 domain",
        "link": "http://🐈.com/",
        "expected_output": "http://xn--zn8h.com/",
    },
    {
        "descr": "punycode-encoded utf8 domain",
        "link": "http://xn--zn8h.com/",
    },
    {
        "descr": "percent-encode ascii link",
        "link": "http://test.com/%61%62%63/",
        "expected_output": "http://test.com/%61%62%63/",
    },
    {
        "descr": "relative link",
        "link": "http://test.com/test/../abc/",
        "expected_output": "http://test.com/abc/",
    },
    {
        "descr": "percent-encoded relative link",
        "link": "http://test.com/test/%2e%2e/abc/",
        "expected_output": "http://test.com/test/%2e%2e/abc/",
    },
    {
        "descr": "space link",
        "link": "http://test.com/test/a b c/",
        "expected_output": "http://test.com/test/a%20b%20c/",
    },
    {
        "descr": "percent-encoded space link",
        "link": "http://test.com/test/a%20b%20c/",
    },
    {
        "descr": "reserved characters link",
        "link": "http://test.com/, &/",
        "expected_output": "http://test.com/,%20&/",
    },
    {
        "descr": "percent-encoded slash link",
        "link": "http://test.com/test/a%2fb/",
        "expected_output": "http://test.com/test/a%2fb/",
    },
    {
        "descr": "url parameters",
        "link": "http://test.com/?a=b",
    },
    {
        "descr": "url parameters with space",
        "link": "http://test.com/?a=a b",
        "expected_output": "http://test.com/?a=a+b",
    },
    {
        "descr": "url parameters with plus",
        "link": "http://test.com/?a=a+b",
    },
    {
        "descr": "url parameters with percents",
        "link": "http://test.com/?a=a%20b",
        "expected_output": "http://test.com/?a=a+b",
    },
    {
        "descr": "url parameters with slash",
        "link": "http://test.com/?a=a/b",
        "expected_output": "http://test.com/?a=a%2Fb",
    },
    {
        "descr": "url with sharp",
        "link": "http://test.com/test#test/",
        "expected_output": "http://test.com/test",
    },
    {
        "descr": "no trailing slash hostname",
        "link": "http://test.com",
        "expected_output": "http://test.com/",
    },
    {
        "descr": "trailing slash hostname",
        "link": "http://test.com/",
    },
    {
        "descr": "no trailing slash path",
        "link": "http://test.com/test",
    },
    {
        "descr": "trailing slash path",
        "link": "http://test.com/test/",
    },
)

_LINKS = "\n".join([f'<a href="{link["link"]}">{link["descr"]}</a>' for link in LINKS])
FAKE_PAGE = f"""
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"></head>'
  <body>
    {_LINKS}
  </body>
</html>
""".encode()


ATOM_FEED = b"""
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
"""


ATOM_FEED_WITH_HEADER = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ATOM_FEED


RSS_FEED = b"""
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
"""


class PageTest(TransactionTestCase):
    @classmethod
    def tearDownClass(cls):
        BrowserChromium.destroy()
        BrowserFirefox.destroy()

    def setUp(self):
        super().setUp()
        self.crawl_policy = CrawlPolicy.create_default()
        self.crawl_policy.snapshot_html = False
        self.crawl_policy.recursion = CrawlPolicy.CRAWL_ALL
        self.crawl_policy.save()

    def test_10_beautifulsoup(self):
        page = Page("http://127.0.0.1/", FAKE_PAGE, None)
        links = list(page.get_links(True))

        self.assertEqual(len(links), len(LINKS))
        for no, link in enumerate(links):
            expected = LINKS[no].get("expected_output", LINKS[no]["link"])
            self.assertEqual(link, expected, f"{LINKS[no]['descr']} failed")

    NAV_HTML = b'<html><body><header>header</header><nav>nav<a href="link">link</a></nav>text<footer>footer</footer></body></html>'

    def test_20_no_nav_element(self):
        page = Page("http://test/", self.NAV_HTML, None)
        doc = Document.objects.create(url=page.url)
        doc.index(page, self.crawl_policy)
        self.assertEqual(doc.content, "text")
        links = Link.objects.order_by("id")
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].in_nav)

        view = WWWView()
        view.doc = doc
        view.request = None
        www_content = view._get_content()
        self.assertEqual(www_content, ' <a href="/words/http://test/link">link</a>text<br/>')

    def test_30_nav_element(self):
        page = Page("http://test/", self.NAV_HTML, None)
        doc = Document.objects.create(url=page.url)
        self.crawl_policy.remove_nav_elements = CrawlPolicy.REMOVE_NAV_NO
        doc.index(page, self.crawl_policy)
        self.assertEqual(doc.content, "header nav link text footer")

        links = Link.objects.order_by("id")
        self.assertEqual(len(links), 1)
        self.assertFalse(links[0].in_nav)

        view = WWWView()
        view.doc = doc
        www_content = view._get_content()
        self.assertEqual(
            www_content,
            'header nav  <a href="/words/http://test/link">link</a> text footer<br/>',
        )

    DATES = (
        (
            "Wed, 21 Oct 2015 07:28:00 GMT",
            datetime(2015, 10, 21, 7, 28, 0, tzinfo=timezone.utc),
        ),
        (
            "Tue, 22 Feb 2022 22:22:22 GMT",
            datetime(2022, 2, 22, 22, 22, 22, tzinfo=timezone.utc),
        ),
    )

    def test_40_http_date_parse(self):
        for s, d in self.DATES:
            self.assertEqual(http_date_parser(s), d)

    def test_50_http_date_format(self):
        for s, d in self.DATES:
            self.assertEqual(s, http_date_format(d))

    def test_60_no_comment(self):
        page = Page("http://test/", b"<html><body><!-- nothing -->text</body></html>", None)
        doc = Document(url=page.url)
        doc.index(page, self.crawl_policy)
        self.assertEqual(doc.content, "text")

    def test_70_feeds(self):
        for feed in (ATOM_FEED, ATOM_FEED_WITH_HEADER, RSS_FEED):
            page = Page("http://test/", feed, None)
            doc = Document.objects.create(url=page.url)
            doc.index(page, self.crawl_policy)

            self.assertEqual(Document.objects.count(), 4)
            self.assertEqual(doc.url, page.url)
            self.assertEqual(doc.title, "Feed title")
            self.assertEqual(
                doc.content,
                "Feed title\nFeed description\n08/29/2023 10:13 a.m. Entry one\n08/29/2023 10:09 a.m. Entry two\n",
            )
            self.assertIn(doc.mimetype, ("text/xml", "text/html"))

            links = Link.objects.order_by("id")
            self.assertEqual(links.count(), 3)

            self.assertEqual(links[0].text, "Feed title")
            self.assertEqual(links[0].doc_to.url, "http://192.168.120.5/")
            self.assertEqual(links[1].text, "Entry one")
            self.assertEqual(links[1].doc_to.url, "http://192.168.120.5/entry-one")
            self.assertEqual(links[2].text, "Entry two")
            self.assertEqual(links[2].doc_to.url, "http://192.168.120.5/entry-two")

            Document.objects.all().delete()
