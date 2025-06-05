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

from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from .document import Document
from .models import Link, SearchEngine
from .search import add_headlines, get_documents_from_request
from .search_form import SearchForm
from .tag import Tag


class SearchTest(TransactionTestCase):
    def setUp(self):
        self.root = Document.objects.wo_content().create(
            url="http://127.0.0.1/",
            normalized_url="http://127.0.0.1/",
            content="Hello world one two three",
            normalized_content="Hello world one two three",
            title="Root",
            normalized_title="Root",
            crawl_last=timezone.now(),
        )
        self.page = Document.objects.wo_content().create(
            url="http://127.0.0.1/page1",
            normalized_url="http://127.0.0.1/page1",
            content="Page1, World Télé one three",
            normalized_content="Page1, World Tele one three",
            title="Page1",
            normalized_title="Page1",
            crawl_last=timezone.now(),
        )
        self.link = Link.objects.create(doc_from=self.root, doc_to=self.page, text="link text", pos=0, link_no=0)

        self.extern_link = Link.objects.create(
            doc_from=self.page,
            text="extern site",
            pos=0,
            link_no=0,
            extern_url="http://perdu.com",
        )

        self.tag1 = Tag.objects.create(name="tag1")
        self.tag2 = Tag.objects.create(name="tag2")
        self.tag3 = Tag.objects.create(name="tag3")
        self.tagged_page = Document.objects.wo_content().create(
            url="http://127.0.0.1/tagged",
            normalized_url="http://127.0.0.1/tagged",
            content="Tagged, tag one two",
            normalized_content="Tagged, tag one two",
            title="Tagged",
            normalized_title="Tagged",
            crawl_last=timezone.now(),
        )
        self.tagged_page.tags.set([self.tag1, self.tag2])

        self.tagged_page2 = Document.objects.wo_content().create(
            url="http://127.0.0.1/tagged2",
            normalized_url="http://127.0.0.1/tagged2",
            content="Tagged2, tag one three",
            normalized_content="Tagged2, tag one three",
            title="Tagged2",
            normalized_title="Tagged2",
            crawl_last=timezone.now(),
        )
        self.tagged_page2.tags.set([self.tag1])

        self.admin = User.objects.create(username="admin", is_superuser=True, is_staff=True)
        self.admin.set_password("admin")
        self.admin.save()

        self.user = User.objects.create(username="user")
        self.user.set_password("user")
        self.user.save()

    def tearDown(self):
        self.root.delete()
        self.page.delete()

    def _search_docs(self, params, user=None):
        request = WSGIRequest({"REQUEST_METHOD": "GET", "QUERY_STRING": params, "wsgi.input": ""})
        request.user = user or self.admin
        form = SearchForm(request.GET)
        self.assertTrue(form.is_valid(), form.errors)
        return get_documents_from_request(request, form)[1]

    def test_001_q_search(self):
        docs = self._search_docs("q=hello")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_002_doc_contains(self):
        docs = self._search_docs("ft1=inc&ff1=doc&fo1=contain&fv1=hello")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_003_content_contains(self):
        docs = self._search_docs("ft1=inc&ff1=content&fo1=contain&fv1=hello")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_004_url_contains(self):
        docs = self._search_docs("ft1=inc&ff1=url&fo1=contain&fv1=page")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_005_title_contains(self):
        docs = self._search_docs("ft1=inc&ff1=title&fo1=contain&fv1=root")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_006_links_to_url_contains(self):
        docs = self._search_docs("ft1=inc&ff1=lto_url&fo1=contain&fv1=page")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_007_links_to_text_contains(self):
        docs = self._search_docs("ft1=inc&ff1=lto_txt&fo1=contain&fv1=extern")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_010_linked_by_url_contains(self):
        docs = self._search_docs("ft1=inc&ff1=lby_url&fo1=regexp&fv1=^http://127.0.0.1/$")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_011_linked_by_text_contains(self):
        docs = self._search_docs("ft1=inc&ff1=lby_txt&fo1=contain&fv1=text")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_012_regexp(self):
        docs = self._search_docs("ft1=inc&ff1=doc&fo1=regexp&fv1=hel.*")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

        docs = self._search_docs("ft1=inc&ff1=doc&fo1=regexp&fv1=hel[^l]")
        self.assertEqual(docs.count(), 0)

    def test_013_equal(self):
        docs = self._search_docs("ft1=inc&ff1=doc&fo1=equal&fv1=hello world one two three")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

        docs = self._search_docs("ft1=inc&ff1=doc&fo1=equal&fv1=hello")
        self.assertEqual(docs.count(), 0)

    def test_014_case(self):
        docs = self._search_docs("ft1=inc&ff1=doc&fo1=contain&fv1=Hello&fc1=on")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

        docs = self._search_docs("ft1=inc&ff1=doc&fo1=contain&fv1=hello&fc1=on")
        self.assertEqual(docs.count(), 0)

    def test_015_exclude(self):
        docs = self._search_docs("ft1=exc&ff1=doc&fo1=contain&fv1=Hello")
        self.assertEqual(docs.count(), 3, docs.values_list("url", flat=True))
        self.assertEqual(docs[0], self.page)

    def test_016_web_match(self):
        docs = self._search_docs("q=world")
        self.assertEqual(docs.count(), 2)

    def test_017_web_not_match(self):
        docs = self._search_docs("q=-hello")
        self.assertEqual(docs.count(), 3)
        self.assertEqual(docs[0], self.page)

    def test_018_web_and(self):
        docs = self._search_docs("q=hello world")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.root)

    def test_019_web_or(self):
        docs = self._search_docs("q=page1")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

        docs = self._search_docs("q=hello or page1")
        self.assertEqual(docs.count(), 2)

    def test_020_web_exact(self):
        docs = self._search_docs('q="one three"')
        self.assertEqual(docs.count(), 2)
        self.assertEqual(docs[0], self.page)

    def test_021_headline(self):
        request = WSGIRequest({"REQUEST_METHOD": "GET", "QUERY_STRING": "q=tele", "wsgi.input": ""})
        request.user = self.admin
        form = SearchForm(request.GET)
        self.assertTrue(form.is_valid())
        _, docs, query = get_documents_from_request(request, form)
        docs = add_headlines(docs, query)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)
        self.assertEqual(docs[0].headline, 'Page1, World <span class="res-highlight">Télé</span>')

    def test_030_hidden(self):
        self.root.hidden = True
        self.root.save()
        docs = self._search_docs('q="world"')
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

        docs = self._search_docs('q="world"', user=self.user)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_040_hidden_included(self):
        self.root.hidden = True
        self.root.save()
        docs = self._search_docs('q="world"&i=on')
        self.assertEqual(docs.count(), 2)
        self.assertEqual(list(docs), [self.page, self.root])

        docs = self._search_docs('q="world"&i=on', user=self.user)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_050_search_tag(self):
        docs = self._search_docs(f"tag={self.tag1.id}")
        self.assertEqual(docs.count(), 2)
        self.assertEqual(list(docs), [self.tagged_page, self.tagged_page2])

        docs = self._search_docs(f"tag={self.tag2.id}")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.tagged_page)

        docs = self._search_docs(f"tag={self.tag1.id}&tag={self.tag2.id}")
        self.assertEqual(docs.count(), 1, docs.values_list("url", flat=True))
        self.assertEqual(docs[0], self.tagged_page)

        docs = self._search_docs(f"tag={self.tag3.id}")
        self.assertEqual(docs.count(), 0)

        docs = self._search_docs(f"tag={self.tag1.id}&tag={self.tag3.id}")
        self.assertEqual(docs.count(), 0)

    def test_060_search_tag_includes_children(self):
        subtag = Tag.objects.create(name="subtag", parent=self.tag1)
        self.page.tags.add(subtag)

        docs = self._search_docs(f"tag={self.tag1.id}")
        self.assertEqual(docs.count(), 3, docs)
        self.assertEqual(
            sorted(docs, key=lambda x: x.id),
            sorted([self.tagged_page, self.tagged_page2, self.page], key=lambda x: x.id),
        )

        docs = self._search_docs(f"tag={subtag.id}")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)

    def test_070_search_tag_param(self):
        docs = self._search_docs(f"ft1=inc&ff1=tag&fo1=contain&fv1={self.tag1.name}")
        self.assertEqual(docs.count(), 2, docs.values_list("url", flat=True))
        self.assertEqual(list(docs), [self.tagged_page, self.tagged_page2])

        docs = self._search_docs(f"ft1=inc&ff1=tag&fo1=contain&fv1={self.tag2.name}")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.tagged_page)

        docs = self._search_docs(
            f"ft1=inc&ff1=tag&fo1=contain&fv1={self.tag1.name}&ft2=inc&ff2=tag&fo2=contain&fv2={self.tag2.name}"
        )
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.tagged_page)

        docs = self._search_docs(f"ft1=inc&ff1=tag&fo1=contain&fv1={self.tag3.name}")
        self.assertEqual(docs.count(), 0)

        docs = self._search_docs(
            f"ft1=inc&ff1=tag&fo1=contain&fv1={self.tag1.name}&ft2=inc&ff2=tag&fo2=contain&fv2={self.tag3.name}"
        )
        self.assertEqual(docs.count(), 0)

    def test_080_search_tag_includes_children(self):
        subtag = Tag.objects.create(name="subtag", parent=self.tag1)
        self.page.tags.add(subtag)

        docs = self._search_docs(f"ft1=inc&ff1=tag&fo1=contain&fv1={self.tag1.name}")
        self.assertEqual(docs.count(), 3)
        self.assertEqual(
            sorted(docs, key=lambda x: x.id),
            sorted([self.tagged_page, self.tagged_page2, self.page], key=lambda x: x.id),
        )

        docs = self._search_docs(f"ft1=inc&ff1=tag&fo1=contain&fv1={subtag.name}")
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs[0], self.page)


class ShortcutTest(TransactionTestCase):
    def setUp(self):
        self.se = SearchEngine.objects.create(
            short_name="fake",
            shortcut="f",
            html_template=self._search_url("{searchTerms}"),
        )
        SearchEngine.objects.create(
            short_name="fake2",
            shortcut="g",
            html_template=self._search_url("{searchTerms}", "test2.com"),
        )

    def _search_url(self, term, se="test.com"):
        return f"http://{se}/?q={term}"

    def test_10_search(self):
        self.assertEqual(SearchEngine.should_redirect("test"), None)
        self.assertEqual(SearchEngine.should_redirect("!f test"), self._search_url("test"))
        self.assertEqual(
            SearchEngine.should_redirect("!g test"),
            self._search_url("test", "test2.com"),
        )

    @override_settings(SOSSE_SEARCH_SHORTCUT_CHAR="+")
    def test_20_custom_shortcut(self):
        self.assertEqual(SearchEngine.should_redirect("!f test"), None)
        self.assertEqual(SearchEngine.should_redirect("+f test"), self._search_url("test"))
        self.assertEqual(
            SearchEngine.should_redirect("+g test"),
            self._search_url("test", "test2.com"),
        )

    @override_settings(SOSSE_DEFAULT_SEARCH_REDIRECT="fake")
    def test_30_custom_default(self):
        self.assertEqual(SearchEngine.should_redirect("test"), self._search_url("test"))
        self.assertEqual(SearchEngine.should_redirect("!f test"), self._search_url("test"))
        self.assertEqual(
            SearchEngine.should_redirect("!g test"),
            self._search_url("test", "test2.com"),
        )
        self.assertEqual(SearchEngine.should_redirect(""), None)
        self.assertEqual(SearchEngine.should_redirect(" "), None)

    @override_settings(SOSSE_DEFAULT_SEARCH_REDIRECT="fake", SOSSE_SOSSE_SHORTCUT="s")
    def test_40_sosse_shortcut(self):
        self.assertEqual(SearchEngine.should_redirect("test"), self._search_url("test"))
        self.assertEqual(SearchEngine.should_redirect("!f test"), self._search_url("test"))
        self.assertEqual(
            SearchEngine.should_redirect("!g test"),
            self._search_url("test", "test2.com"),
        )
        self.assertEqual(SearchEngine.should_redirect("!s test"), None)

    def test_50_shortcut_disable(self):
        self.se.enabled = False
        self.se.save()
        SearchEngine.objects.create(
            short_name="fake enabled",
            shortcut="f",
            html_template=self._search_url("{searchTerms}", "test-enabled.com"),
        )

        self.assertEqual(SearchEngine.should_redirect("!f test"), self._search_url("test", "test-enabled.com"))
