Website indexing & Search
=========================

Sosse allows you to crawl a website and search its pages for specific keywords. This process involves configuring
a :doc:`Collection <../crawl/collections>` to define how the site is crawled, followed by searching for the desired
content.

Starting the Crawl
------------------

To begin crawling, go to the :doc:`Crawl a new URL <../crawl/new_url>` page and enter the site's homepage URL.

Review the parameters, then click ``Add to Crawl Queue``. Sosse will crawl the site and add pages to the Collection.

.. note::
   If pages aren’t crawled as expected, check whether the site’s `robots.txt` file is blocking the crawler.
   *Bypass it only if authorized.* You can review this setting in the :doc:`../domains` for the website.


Collection Setup
----------------

Collections control how Sosse accesses and logs website content. This section covers key settings; for full details,
see the :doc:`Collections <../crawl/collections>` documentation.

By default, the crawler processes only directly queued pages. Enabling recursion ensures linked pages are also crawled:

- In the ``⚡ Crawl`` tab, enter a regular expression to match URLs for crawling.
- In the ``🔖 Archive`` tab, disable ``Archive content`` if you only need to search pages without archiving.
- In the ``🕑 Recurrence`` tab, adjust the crawl frequency as needed.

.. note::
   By default, Sosse archives pages, detects if a browser is required for rendering, and adjusts crawl frequency based
   on site updates. Modify the collection to optimize crawl speed or reduce disk usage.

.. image:: ../../../tests/robotframework/screenshots/guide_search_collection.png
   :class: sosse-screenshot

Searching the Website
---------------------

Once crawling is complete, search for keywords directly from the homepage.

For advanced search options, see the :doc:`search parameters <../user/search>` documentation.

Additional Resources
--------------------

- See :doc:`../crawl/collections` for advanced crawling strategies.
- Explore the :doc:`../guides` for further assistance.
