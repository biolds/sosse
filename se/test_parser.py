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

import base64

from django.test import TestCase

from se.browser import Browser, SeleniumBrowser, Page
from se.models import CrawlPolicy


LINKS = ({
    'descr': 'regular link',
    'link': 'http://test.com/',
}, {
    'descr': 'percent-encoded utf8 link',
    'link': 'http://test.com/%F0%9F%90%88/',
}, {
    'descr': 'utf8 link',
    'link': 'http://test.com/🐈/',
    'expected_output': 'http://test.com/%F0%9F%90%88/',
}, {
    'descr': 'utf8 domain',
    'link': 'http://🐈.com/',
    'expected_output': 'http://xn--zn8h.com/',
}, {
    'descr': 'punycode-encoded utf8 domain',
    'link': 'http://xn--zn8h.com/',
}, {
    'descr': 'percent-encode ascii link',
    'link': 'http://test.com/%61%62%63/',
    'expected_output': 'http://test.com/abc/',
}, {
    'descr': 'relative link',
    'link': 'http://test.com/test/../abc/',
    'expected_output': 'http://test.com/abc/'
}, {
    'descr': 'percent-encoded relative link',
    'link': 'http://test.com/test/%2e%2e/abc/',
    'expected_output': 'http://test.com/abc/'
}, {
    'descr': 'space link',
    'link': 'http://test.com/test/a b c/',
    'expected_output': 'http://test.com/test/a%20b%20c/',
}, {
    'descr': 'percent-encoded space link',
    'link': 'http://test.com/test/a%20b%20c/',
}, {
    'descr': 'special characters link',
    'link': 'http://test.com/, &/',
    'expected_output': 'http://test.com/%2C%20%26/',
}, {
    'descr': 'percent-encoded slash link',
    'link': 'http://test.com/test/a%2fb/',
    'expected_output': 'http://test.com/test/a/b/',
}, {
    'descr': 'url parameters',
    'link': 'http://test.com/?a=b',
}, {
    'descr': 'url parameters with space',
    'link': 'http://test.com/?a=a b',
    'expected_output': 'http://test.com/?a=a+b',
}, {
    'descr': 'url parameters with plus',
    'link': 'http://test.com/?a=a+b',
}, {
    'descr': 'url parameters with percents',
    'link': 'http://test.com/?a=a%20b',
    'expected_output': 'http://test.com/?a=a+b',
}, {
    'descr': 'url parameters with slash',
    'link': 'http://test.com/?a=a/b',
    'expected_output': 'http://test.com/?a=a%2Fb',
}, {
    'descr': 'url with sharp',
    'link': 'http://test.com/test#test/',
    'expected_output': 'http://test.com/test',
}, {
    'descr': 'no trailing slash hostname',
    'link': 'http://test.com',
    'expected_output': 'http://test.com/',
}, {
    'descr': 'trailing slash hostname',
    'link': 'http://test.com/',
}, {
    'descr': 'no trailing slash path',
    'link': 'http://test.com/test',
}, {
    'descr': 'trailing slash path',
    'link': 'http://test.com/test/',
})

FAKE_PAGE = '''
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"></head>'
  <body>
    %s
  </body>
</html>
''' % '\n'.join(['<a href="%s">%s</a>' % (link['link'], link['descr']) for link in LINKS])


class PageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        Browser.init()
        CrawlPolicy.create_default()

    @classmethod
    def tearDownClass(cls):
        Browser.destroy()

    def test_10_beautifulsoup(self):
        page = Page('', FAKE_PAGE, None)
        links = list(page.get_links(True))

        self.assertEqual(len(links), len(LINKS))
        for no, link in enumerate(links):
            expected = LINKS[no].get('expected_output', LINKS[no]['link'])
            self.assertEqual(link, expected, '%s failed' % LINKS[no]['descr'])

    def test_20_chromium(self):
        url = 'data:text/html;base64,' + base64.b64encode(FAKE_PAGE.encode('utf-8')).decode('utf-8')
        page = SeleniumBrowser.get(url)
        links = list(page.get_links(True))

        self.assertEqual(len(links), len(LINKS))
        for no, link in enumerate(links):
            expected = LINKS[no].get('expected_output', LINKS[no]['link'])
            self.assertEqual(link, expected, '%s failed' % LINKS[no]['descr'])
