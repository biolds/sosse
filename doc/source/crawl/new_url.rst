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

When adding URLs to the queue, you can choose a crawling scope:

* **Keep collection settings unchanged**: Use the :doc:`collection's <collections>` existing regex patterns without
  modification
* **Crawl entire websites (unlimited depth)**: Automatically add the URL hostnames to the :doc:`collection's
  <collections>` unlimited regex, allowing full crawling of those websites
* **Crawl with depth limit from collection settings**: Add the URL hostnames to the :doc:`collection's <collections>`
  limited regex, applying the :doc:`collection's <collections>` recursion depth limit

The crawling scope setting automatically extracts hostnames from the submitted URLs and adds appropriate regex patterns
to the selected :doc:`collection <collections>`. This provides a convenient way to expand crawling scope without
manually editing :doc:`collection <collections>` regex patterns.

To control how pages are indexed and whether recursion occurs, update the relevant settings in :doc:`collections`.

After submitting a URL, the next page shows the :doc:`queue`.
