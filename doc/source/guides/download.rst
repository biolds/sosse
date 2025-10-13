File Downloads
==============

Sosse allows for the automation of file downloads from websites. The example
below demonstrates how to download new
eBooks daily from `Project Gutenberg <https://www.gutenberg.org>`_.

`Project Gutenberg <https://www.gutenberg.org>`_ is a digital library offering
over 75,000 free eBooks, including many
classic literary works.

.. note::
   Project Gutenberg provides several methods for retrieving its content if you
   wish to download it. See the
   `Offline Catalogs and Feeds <https://www.gutenberg.org/ebooks/offline_catalogs.html>`_
   for more information. If you
   wish to download the full database, there are more appropriate methods than crawling, such as the
   `Mirroring How-To <https://www.gutenberg.org/help/mirroring.html>`_. 🐞

Collections Setup
-----------------

Collections are essential for controlling how Sosse accesses and downloads content from websites. For more details,
see the :doc:`Collections <../crawl/collections>` documentation.

**Project Gutenberg Collection**

- In the ``⚡ Crawl`` tab, set ``Unlimited depth URL regex``::

    ^http://www.gutenberg.org/cache/epub/feeds/today.rss$
    ^https://www.gutenberg.org/ebooks/[0-9]+$
    ^https://www.gutenberg.org/ebooks/[0-9]+.epub3.images$
    ^https://www.gutenberg.org/cache/epub/.*epub$

- In the ``🔖 Archive`` tab, ensure ``Archive content`` is enabled to download the EPUB files.
- In the ``🕑 Recurrence`` tab, set ``Crawl frequency`` to ``Once`` (as reference pages and books do not need
  updates after initial download). Additionally, clear both the ``Recrawl dt min`` and ``Recrawl dt max`` fields.

.. image:: ../../../tests/robotframework/screenshots/guide_download_collections.png
   :class: sosse-screenshot

Start Crawling
--------------

To start crawling, go to the :doc:`Crawl a new URL <../crawl/new_url>` page and enter the URL of the RSS feed:
``http://www.gutenberg.org/cache/epub/feeds/today.rss``.

Check the parameters, then click ``Add to Crawl Queue``. Once confirmed, you will be able to see the crawl queue
retrieving the files from the feed.

.. image:: ../../../tests/robotframework/screenshots/guide_download_crawl_queue.png
   :class: sosse-screenshot

View the Library
----------------

To view all the books indexed from the RSS feed, go to the homepage and unfold the ``Params`` section. We can
execute a query to fetch all the pages linked within the RSS feed, with the following parameters:

- Sort: ``First crawled descending``.
- Search options:

  - Action: ``Keep``
  - Field: ``Linked by URL``
  - Operator: ``Equal to``
  - Value: ``https://www.gutenberg.org/cache/epub/feeds/today.rss``

This will display all the books that were loaded from the RSS feed.

.. image:: ../../../tests/robotframework/screenshots/guide_download_view_library.png
   :class: sosse-screenshot

Each link will point to the archived page containing information about the book:

.. image:: ../../../tests/robotframework/screenshots/guide_download_archive_html.png
   :class: sosse-screenshot
   :alt: Book Information Page

Following the link, you will be able to download the book:

.. image:: ../../../tests/robotframework/screenshots/guide_download_archive_download.png
   :class: sosse-screenshot
   :alt: EPUB Download Page

Additional Options
------------------

You may want to usethe :ref:`atom feed <ui_atom_feeds>` feature to create an Atom feed that points to the
downloaded EPUB files, which could be useful for integrating with an EPUB reader or sharing updates.
