Types of Archives
=================

Sosse can create different types of snapshots of the pages it crawls. These snapshots can be browsed offline, as
described below.

By default, archived pages can be accessed via the ``archive`` link in the search results. See
:ref:`search results <ui_search_results>`.

🔖 HTML Archive
---------------

By default, the crawlers store HTML pages and the files they depend on (such as images and stylesheets). This behavior
can be controlled in the :ref:`⚡ Collection <collection_archive>`.

It is also possible to use a browser to take the snapshot, in which case the snapshot is taken after the page is
rendered (following JavaScript execution).

All HTML archived pages can be cleared with the :ref:`clear_html_archive <cli_clear_html_archive>` management command.

📷 Screenshots Archive
----------------------

The crawlers can take screenshots of the pages they browse. Pages saved this way also store link information and can be
browsed offline. Screenshots can be enabled in the :ref:`⚡ Collection <collection_take_screenshot>`.

✏ Text Archive
--------------

The text content of all crawled pages is stored. This text archive retains link information and can be used to navigate
to other archived pages. The text archive is created for all indexed documents.

.. _browsable_home:

🏠 Browsable Home
-----------------

.. image:: ../../../tests/robotframework/screenshots/browsable_home.png
   :class: sosse-screenshot

The entry points of crawled websites (the URLs that were manually queued) are displayed on the homepage to easily
navigate archived websites. The websites displayed can be customized using the
:ref:`show on homepage <document_show_on_homepage>` option of documents.

The homepage can be configured to show only the search bar by disabling the
:ref:`browsable home option <conf_option_browsable_home>`.

.. _online_detection:

Online Detection
----------------

When the :ref:`online_search_redirect option <conf_option_online_search_redirect>` is set, making a search will
redirect the user to the ``online_search_redirect`` defined search engine when Sosse is online, or initiate a Sosse
search if offline. Searching locally or online can be forced from the :ref:`User profile <pref_online_mode>`.
