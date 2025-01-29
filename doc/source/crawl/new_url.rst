🌐 Crawl a new URL
==================

In the |conf_menu_button| menu, or in the :doc:`../admin_ui`, by clicking ``🌐 Crawl a new URL`` you can queue one or
multiple URLs to be crawled when a worker is available.

.. |conf_menu_button| image:: ../../../tests/robotframework/screenshots/conf_menu_button.png
   :class: sosse-inline-screenshot

.. image:: ../../../tests/robotframework/screenshots/crawl_new_url.png
   :class: sosse-screenshot

By default, only the URLs queued for crawling will be visited. The crawler will not recurse into discovered links unless
explicitly configured.

To control how pages are indexed and whether recursion occurs, update the relevant settings in :doc:`policies`.

After submitting a URL, the next page shows the :doc:`queue`.
