Offline browsing, cached pages
==============================

Cached pages can be access from the search results, by clicking the ``Cache`` link.

.. image:: ../../../tests/robotframework/screenshots/cache_info.png
   :class: sosse-screenshot
   :scale: 50%

The top part of the page shows information about the indexed page.

When the :doc:`Crawl Policy <../crawl/policies>` has screenshots enabled,
the cached page shows the screenshot and links to other indexed page can be clicked:

.. image:: ../../../tests/robotframework/screenshots/cache_screenshot.png
   :class: sosse-screenshot
   :scale: 50%

The ``Text version`` links to the text version of the page. The ``Word weights`` shows the weight of
stemmed words in the page, these are used to calculate the score of the page in the :doc:`search results <search>`.
