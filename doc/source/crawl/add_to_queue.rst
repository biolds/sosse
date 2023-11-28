Adding URLs to the crawl queue
==============================

In the |conf_menu_button| menu, or in the :doc:`../admin_ui`, by clicking ``🌐 Crawl a new URL`` you can queue an URL that will be crawled when a worker is available.

.. |conf_menu_button| image:: ../../../tests/robotframework/screenshots/conf_menu_button.png
   :class: sosse-inline-screenshot

.. image:: ../../../tests/robotframework/screenshots/crawl_new_url.png
   :class: sosse-screenshot

By default, all links found in the page will be visited and the crawlers will recurse until all pages are discovered. Submitting redirects to
the :doc:`status` page.

How pages are indexed and which pages to recurse into is defined by :doc:`policies`.
