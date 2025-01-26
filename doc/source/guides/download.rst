File Downloads
==============

SOSSE allows for the automation of file downloads from websites. The example below demonstrates how to download new
eBooks daily from `Project Gutenberg <https://www.gutenberg.org>`_.

`Project Gutenberg <https://www.gutenberg.org>`_ is a digital library offering over 75,000 free eBooks, including many
classic literary works.

.. note::
   Project Gutenberg provides several methods for retrieving its content if you wish to download it. See the
   `Offline Catalogs and Feeds <https://www.gutenberg.org/ebooks/offline_catalogs.html>`_ for more information. If you
   wish to download the full database, there are more appropriate methods than crawling, such as the
   `Mirroring How-To <https://www.gutenberg.org/help/mirroring.html>`_. 🐞

Creating Crawl Policies
-----------------------

Crawl policies are essential for controlling how SOSSE accesses and downloads content from websites. For more details,
see the :doc:`Crawl Policies <../crawl/policies>` documentation. The default policy will crawl any link it finds, we
will modify this behavior to ensure that only specified pages are crawled.

Additionally, we will create the following policies:

1. A policy that reads the RSS feed of Project Gutenberg daily to monitor new content.
2. A policy to download the reference page and the EPUB version of the book for each new title identified in the RSS
   feed.

Modifying the Default Policy
----------------------------

To modify the default policy, edit the ``(default)`` policy (see the :doc:`Crawl Policy <../crawl/policies>`), and set
the ``Recursion`` parameter to ``Never crawl`` instead of ``Crawl all pages``.

.. image:: ../../../tests/robotframework/screenshots/guide_download_default_policy.png
   :class: sosse-screenshot

Creating New Policies for Project Gutenberg
-------------------------------------------

For the Project Gutenberg pages, we will create two new policies:

- **RSS Feed Policy:** create the policy and set up the following parameters:

  - In the ``⚡ Crawl`` tab, use a regular expression ``^http://www.gutenberg.org/cache/epub/feeds/today.rss$`` to
    target the daily RSS feed. Set ``Thumbnail mode`` to ``No thumbnail`` (this disables the screenshot thumbnail,
    allowing the crawl to run without a browser for faster processing).
  - In the ``🌍 Browser`` tab, set ``Default browse mode`` to ``Python Request``.
  - In the ``🔖 Archive`` tab, disable ``Archive content`` (as we don't need to archive the original feed).
  - In the ``🕑 Recurrence`` tab, set ``Crawl frequency`` to ``Constant time`` and clear the ``Recrawl dt max``
    field.

- **Book Download Policy:** create this policy and set up the following parameters:

  - In the ``⚡ Crawl`` tab, use the regular expressions ``^https://www.gutenberg.org/ebooks/[0-9]+$`` for the
    reference page, ``^https://www.gutenberg.org/ebooks/[0-9]+.epub3.images$`` and
    ``^https://www.gutenberg.org/cache/epub/.*epub$`` for the EPUB files. Set ``Thumbnail mode`` to
    ``Page preview from metadata`` (this disables the screenshot thumbnail, allowing the crawl to run without a
    browser for faster processing).
  - In the ``🌍 Browser`` tab, set ``Default browse mode`` to ``Python Request`` (since Project Gutenberg does not
    require a browser to render pages correctly).
  - In the ``🕑 Recurrence`` tab, set ``Crawl frequency`` to ``Once`` (since the reference pages and books will not be
    updated, and we only need to download them once). Additionally, clear both the ``Recrawl dt min`` and
    ``Recrawl dt max`` fields.

.. image:: ../../../tests/robotframework/screenshots/guide_download_crawl_policies.png
   :class: sosse-screenshot

Start Crawling
--------------

To start crawling, go to the :doc:`Crawl a new URL <../crawl/new_url>` page and enter the URL od the RSS feed:
``http://www.gutenberg.org/cache/epub/feeds/today.rss``.

Check the parameters, then click ``Confirm``. Once confirmed, you will be able to see the crawl queue retrieving the
files from the feed.

.. image:: ../../../tests/robotframework/screenshots/guide_download_crawl_queue.png
   :class: sosse-screenshot

View the Library
----------------

To view all the books indexed from the RSS feed, go to the homepage and unfold the ``Params`` section. We can
execute a query to fetch all the pages linked within the RSS feed, with the following parameters:

- Sort: ``First crawled descending``.
- Search options:
  - Acion: ``Keep``
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

You may also be interested in the :ref:`max_file_size <conf_option_max_file_size>` (defaults to 500 kB) and
:ref:`max_html_asset_size <conf_option_max_html_asset_size>` (defaults to 5 MB) configuration options, which control the
size limits of files being downloaded.

Additionally, you can use the :ref:`atom feed <ui_atom_feeds>` feature to create an Atom feed that points to the
downloaded EPUB files, which could be useful for integrating with an EPUB reader or sharing updates.
