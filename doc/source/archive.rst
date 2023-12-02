Archiving
=========

SOSSE can create different kind of snapshot of the pages it crawls. These snapshot can be browsed offline, as described below.

By default, cached pages can be accessed using the ``cached`` link in the search results, see :ref:`search results <ui_search_results>`. Archived pages can also be displayed on the homepage, see the :ref:`Browsable home <browsable_home>` option below.

Text cache
----------

The text content of all crawled page is stored. This text cache retains links information and can be used to reach other cached pages.

HTML snapshots
--------------

By default, the crawlers store HTML pages and files it depends on (images, stylesheets...). This behaviour can be controlled in the :ref:`⚡ Crawl policy <policy_html_snapshot>`.

It is possible to use a browser to take the snapshot, in this case the snapshot is taken after the page is rendered (after Javascript execution).

The HTML snapshoting process uses a cache that can be cleared with a :ref:`management command <cli_clear_cache>`.

Page screenshots
----------------

The crawlers can take screenshots of pages they browse. Pages saved this way also store link informations and can be browsed offline. Screenshots can be enabled in the :ref:`⚡ Crawl policy <policy_take_screenshot>`.

.. _browsable_home:

Browsable home
--------------

.. image:: ../../tests/robotframework/screenshots/browsable_home.png
   :class: sosse-screenshot

The :ref:`browsable home option <conf_option_browsable_home>` can be enabled to display the list of archived websites on the homepage. When enabled, all entry points URL crawled are displayed (see :doc:`crawl/add_to_queue`) are shown. Displayed website can be customized using the :ref:`show on homepage <document_show_on_homepage>` option of documents.

.. _online_detection:

Online detection
----------------

When the :ref:`online_search_redirect option <conf_option_online_search_redirect>` is set, making a search would redirect the user to the ``online_search_redirect`` defined search engine when SOSSE is online, or make a SOSSE search otherwise. Searching locally or online can forced from the :ref:`User preferences <pref_online_mode>`.
