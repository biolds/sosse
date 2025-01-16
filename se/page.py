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

from bs4 import BeautifulSoup, Comment, Doctype, Tag
from magic import from_buffer as magic_from_buffer

from .url import (
    absolutize_url,
    has_browsable_scheme,
    sanitize_url,
    url_remove_fragment,
    url_remove_query_string,
)

NAV_ELEMENTS = ["nav", "header", "footer"]


class Page:
    def __init__(self, url, content, browser, headers=None, status_code=None):
        if not isinstance(content, bytes):
            raise ValueError("content must be bytes")
        self.url = sanitize_url(url)
        self.content = content
        self.redirect_count = 0
        self.title = None
        self.soup = None
        self.browser = browser
        self.headers = headers or {}
        self.status_code = status_code

        # dirty hack to avoid some errors (as triggered since bookworm during tests)
        magic_head = self.content[:20].strip().lower()
        is_html = False
        for header in ("<html", "<!doctype html"):
            is_html |= isinstance(magic_head, str) and magic_head.startswith(header)
            is_html |= isinstance(magic_head, bytes) and magic_head.startswith(header.encode("utf-8"))

        if is_html:
            self.mimetype = "text/html"
        else:
            self.mimetype = magic_from_buffer(self.content, mime=True)

    def get_soup(self):
        if self.soup:
            return self.soup
        if not self.mimetype or not self.mimetype.startswith("text/"):
            return None
        content = self.content.decode("utf-8", errors="replace")
        self.soup = BeautifulSoup(content, "html5lib")

        # Remove <template> tags as BS extract its text
        for elem in self.soup.find_all("template"):
            elem.extract()
        return self.soup

    def get_links(self, keep_params):
        for a in self.get_soup().find_all("a"):
            if a.get("href"):
                url = absolutize_url(self.url, a.get("href").strip())
                if not keep_params:
                    url = url_remove_query_string(url)
                url = url_remove_fragment(url)
                yield url

    def update_soup(self, soup):
        self.soup = soup

    def dump_html(self):
        return self.get_soup().encode()

    def base_url(self):
        soup = self.get_soup()

        base_url = self.url
        if soup.head.base and soup.head.base.get("href"):
            base_url = absolutize_url(self.url, soup.head.base.get("href"))
            base_url = url_remove_fragment(base_url)
        return base_url

    def remove_nav_elements(self):
        soup = self.get_soup()
        for elem_type in NAV_ELEMENTS:
            for elem in soup.find_all(elem_type):
                elem.extract()

    def _get_elem_text(self, elem, recurse=False):
        s = ""
        if elem.name is None:
            s = getattr(elem, "string", "") or ""
            s = s.strip(" \t\n\r")

        if (elem.name == "a" or recurse) and hasattr(elem, "children"):
            for child in elem.children:
                _s = self._get_elem_text(child, True)
                if _s:
                    if s:
                        s += " "
                    s += _s
        return s

    def _build_selector(self, elem):
        no = 1
        for sibling in elem.previous_siblings:
            if isinstance(elem, Tag) and sibling.name == elem.name:
                no += 1

        selector = f"/{elem.name}[{no}]"

        if elem.name != "html":
            selector = self._build_selector(elem.parent) + selector
        return selector

    def _dom_walk(self, elem, crawl_policy, links, queue_links, document, in_nav=False):
        from .crawl_policy import CrawlPolicy
        from .document import Document
        from .models import Link

        if queue_links != (document is not None):
            raise Exception(f"document parameter ({document}) is required to queue links ({queue_links})")

        if isinstance(elem, (Doctype, Comment)):
            return

        if elem.name in ("[document]", "title", "script", "style"):
            return

        if crawl_policy.remove_nav_elements != CrawlPolicy.REMOVE_NAV_NO and elem.name in ("nav", "header", "footer"):
            in_nav = True

        s = self._get_elem_text(elem)

        # Keep the link if it has text, or if we take screenshots
        if elem.name in (None, "a"):
            if links["text"] and links["text"][-1] not in (" ", "\n") and s and not in_nav:
                links["text"] += " "

            if elem.name == "a" and queue_links:
                href = elem.get("href")
                if href:
                    link = None
                    target_doc = None
                    href = href.strip()

                    if has_browsable_scheme(href):
                        href_for_policy = absolutize_url(self.base_url(), href)
                        child_policy = CrawlPolicy.get_from_url(href_for_policy)
                        href = absolutize_url(self.base_url(), href)
                        if not child_policy.keep_params:
                            href = url_remove_query_string(href)
                        href = url_remove_fragment(href)
                        target_doc = Document.queue(href, crawl_policy, document)

                        if target_doc != document:
                            if target_doc:
                                link = Link(
                                    doc_from=document,
                                    link_no=len(links["links"]),
                                    doc_to=target_doc,
                                    text=s,
                                    pos=len(links["text"]),
                                    in_nav=in_nav,
                                )

                    store_extern_link = not has_browsable_scheme(href) or target_doc is None
                    if crawl_policy.store_extern_links and store_extern_link:
                        href = elem.get("href").strip()
                        try:
                            href = absolutize_url(self.base_url(), href)
                        except ValueError:
                            # Store the url as is if it's invalid
                            pass
                        link = Link(
                            doc_from=document,
                            link_no=len(links["links"]),
                            text=s,
                            pos=len(links["text"]),
                            extern_url=href,
                            in_nav=in_nav,
                        )

                    if link:
                        if crawl_policy.take_screenshots:
                            link.css_selector = self._build_selector(elem)
                        links["links"].append(link)

            if s and not in_nav:
                links["text"] += s

            if elem.name == "a":
                return

        if hasattr(elem, "children"):
            for child in elem.children:
                self._dom_walk(child, crawl_policy, links, queue_links, document, in_nav)

        if elem.name in ("div", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            if links["text"] and not in_nav:
                if links["text"][-1] == " ":
                    links["text"] = links["text"][:-1] + "\n"
                elif links["text"][-1] != "\n":
                    links["text"] += "\n"

    def dom_walk(self, crawl_policy, queue_links, document):
        links = {"links": [], "text": ""}
        for elem in self.get_soup().children:
            self._dom_walk(elem, crawl_policy, links, queue_links, document, False)
        return links
