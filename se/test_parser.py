# Copyright 2022-2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

# This file checks url conversion (percent encoding, punycode, spaces ...) and consistencies
# across classes and external libraries

from datetime import datetime, timezone

from django.test import TransactionTestCase

from .browser_chromium import BrowserChromium
from .browser_firefox import BrowserFirefox
from .collection import Collection
from .document import Document
from .models import Link
from .page import Page
from .utils import http_date_format, http_date_parser
from .www import WWWView

TEST_URL = "http://test/"

LINKS = (
    {
        "descr": "regular link",
        "link": TEST_URL,
    },
    {
        "descr": "percent-encoded utf8 link",
        "link": f"{TEST_URL}%F0%9F%90%88/",
    },
    {
        "descr": "utf8 link",
        "link": f"{TEST_URL}🐈/",
        "expected_output": f"{TEST_URL}%F0%9F%90%88/",
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
        "link": f"{TEST_URL}%61%62%63/",
        "expected_output": f"{TEST_URL}%61%62%63/",
    },
    {
        "descr": "relative link",
        "link": f"{TEST_URL}test/../abc/",
        "expected_output": f"{TEST_URL}abc/",
    },
    {
        "descr": "percent-encoded relative link",
        "link": f"{TEST_URL}test/%2e%2e/abc/",
        "expected_output": f"{TEST_URL}test/%2e%2e/abc/",
    },
    {
        "descr": "space link",
        "link": f"{TEST_URL}test/a b c/",
        "expected_output": f"{TEST_URL}test/a%20b%20c/",
    },
    {
        "descr": "percent-encoded space link",
        "link": f"{TEST_URL}test/a%20b%20c/",
    },
    {
        "descr": "reserved characters link",
        "link": f"{TEST_URL}, &/",
        "expected_output": f"{TEST_URL},%20&/",
    },
    {
        "descr": "percent-encoded slash link",
        "link": f"{TEST_URL}test/a%2fb/",
        "expected_output": f"{TEST_URL}test/a%2fb/",
    },
    {
        "descr": "url parameters",
        "link": f"{TEST_URL}?a=b",
    },
    {
        "descr": "url parameters with space",
        "link": f"{TEST_URL}?a=a b",
        "expected_output": f"{TEST_URL}?a=a+b",
    },
    {
        "descr": "url parameters with plus",
        "link": f"{TEST_URL}?a=a+b",
    },
    {
        "descr": "url parameters with percents",
        "link": f"{TEST_URL}?a=a%20b",
        "expected_output": f"{TEST_URL}?a=a+b",
    },
    {
        "descr": "url parameters with slash",
        "link": f"{TEST_URL}?a=a/b",
        "expected_output": f"{TEST_URL}?a=a%2Fb",
    },
    {
        "descr": "url with sharp",
        "link": f"{TEST_URL}test#test/",
        "expected_output": f"{TEST_URL}test",
    },
    {
        "descr": "no trailing slash hostname",
        "link": TEST_URL.rstrip("/"),
        "expected_output": TEST_URL,
    },
    {
        "descr": "trailing slash hostname",
        "link": TEST_URL,
    },
    {
        "descr": "no trailing slash path",
        "link": f"{TEST_URL}test",
    },
    {
        "descr": "trailing slash path",
        "link": f"{TEST_URL}test/",
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


ATOM_FEED = f"""
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Feed title</title>
  <description>Feed description</description>
  <link href="{TEST_URL}/other"/>
  <updated>2023-08-29T10:13:27.161859+00:00</updated>
  <id>urn:uuid:02439bf8-bb91-83a1-12e2-f71bb60a0b73</id>
  <icon>{TEST_URL}static/logo.svg</icon>
  <entry>
    <title>Entry one</title>
    <link href="{TEST_URL}entry-one"/>
    <id>urn:uuid:029c6cf9-f277-f085-f2e0-f670aab4f7d0</id>
    <updated>2023-08-29T10:13:27.161859+00:00</updated>
    <summary>Summary one</summary>
  </entry>
  <entry>
    <title>Entry two</title>
    <link href="{TEST_URL}entry-two"/>
    <id>urn:uuid:ad96514e-0246-0892-8e07-0b3d84ced537</id>
    <updated>2023-08-29T10:09:08.250034+00:00</updated>
    <summary>Summary two</summary>
  </entry>
</feed>
""".encode()


ATOM_FEED_WITH_HEADER = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ATOM_FEED


RSS_FEED = f"""
<rss version="2.0">
  <channel>
    <title>Feed title</title>
    <link>{TEST_URL}/other</link>
    <description>Feed description</description>
    <language>en</language>
    <item>
      <title>Entry one</title>
      <link>{TEST_URL}entry-one</link>
      <description>Summary one</description>
      <author>test@exemple.org</author>
      <pubDate>Wed, 29 Aug 2023 10:13:27 GMT</pubDate>
    </item>
    <item>
      <title>Entry two</title>
      <link>{TEST_URL}entry-two</link>
      <description>Summary two</description>
      <author>test@exemple.org</author>
      <pubDate>Wed, 29 Aug 2023 10:09:08 GMT</pubDate>
    </item>
  </channel>
</rss>
""".encode()


class PageTest(TransactionTestCase):
    @classmethod
    def tearDownClass(cls):
        BrowserChromium.destroy()
        BrowserFirefox.destroy()

    def setUp(self):
        super().setUp()
        self.collection = Collection.create_default()
        self.collection.unlimited_regex = TEST_URL
        self.collection.snapshot_html = False
        self.collection.save()

    def test_10_beautifulsoup(self):
        page = Page(TEST_URL, FAKE_PAGE, None)
        links = list(page.get_links(True))

        self.assertEqual(len(links), len(LINKS))
        for no, link in enumerate(links):
            expected = LINKS[no].get("expected_output", LINKS[no]["link"])
            self.assertEqual(link, expected, f"{LINKS[no]['descr']} failed")

    NAV_HTML = b'<html><body><header>header</header><nav>nav<a href="link">link</a></nav>text<footer>footer</footer></body></html>'

    def test_20_remove_nav_from_index(self):
        page = Page(TEST_URL, self.NAV_HTML, None)
        doc = Document.objects.wo_content().create(url=page.url, collection=self.collection)
        doc.index(page, self.collection)
        self.assertEqual(doc.content, "text")
        links = Link.objects.order_by("id")
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].in_nav)

        view = WWWView()
        view.doc = doc
        view.request = None
        www_content = view._get_content()
        self.assertEqual(www_content, f' <a href="/words/{self.collection.id}/{TEST_URL}link">link</a>text<br/>')

    def test_30_remove_nav_no(self):
        page = Page(TEST_URL, self.NAV_HTML, None)
        doc = Document.objects.wo_content().create(url=page.url, collection=self.collection)
        self.collection.remove_nav_elements = Collection.REMOVE_NAV_NO
        doc.index(page, self.collection)
        self.assertEqual(doc.content, "header nav link text footer")

        links = Link.objects.order_by("id")
        self.assertEqual(len(links), 1)
        self.assertFalse(links[0].in_nav)

        view = WWWView()
        view.doc = doc
        www_content = view._get_content()
        self.assertEqual(
            www_content,
            f'header nav  <a href="/words/{self.collection.id}/{TEST_URL}link">link</a> text footer<br/>',
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
        page = Page(TEST_URL, b"<html><body><!-- nothing -->text</body></html>", None)
        doc = Document.objects.create(url=page.url, collection=self.collection)
        doc.index(page, self.collection)
        self.assertEqual(doc.content, "text")

    def test_70_feeds(self):
        for feed in (ATOM_FEED, ATOM_FEED_WITH_HEADER, RSS_FEED):
            page = Page(TEST_URL, feed, None)
            doc = Document.objects.wo_content().create(url=page.url, collection=self.collection)
            doc.index(page, self.collection)

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
            self.assertEqual(links[0].doc_to.url, f"{TEST_URL}other")
            self.assertEqual(links[1].text, "Entry one")
            self.assertEqual(links[1].doc_to.url, f"{TEST_URL}entry-one")
            self.assertEqual(links[2].text, "Entry two")
            self.assertEqual(links[2].doc_to.url, f"{TEST_URL}entry-two")

            Document.objects.wo_content().all().delete()
