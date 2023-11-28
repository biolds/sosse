Offline browsing, cached pages
==============================

Cached pages can be access from the search results, by clicking the ``Cache`` link.

.. image:: ../../../tests/robotframework/screenshots/cache_header.png
   :class: sosse-screenshot

When the :doc:`Crawl Policy <../crawl/policies>` has 🔖 HTML snapshots or 📷 screenshots enabled,
the cached page shows the rendered content and links to other indexed page can be clicked:

.. image:: ../../../tests/robotframework/screenshots/cache_screenshot.png
   :class: sosse-screenshot

The ``✏️ Text version`` links to the text version of the page. The ``📚 Word weights`` shows the weight of
stemmed words in the page, these are used to calculate the score of the page in the :doc:`search results <search>`.
