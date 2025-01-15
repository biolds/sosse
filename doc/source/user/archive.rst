Offline browsing, archived pages
================================

Archived pages can be access from the search results, by clicking the ``archive`` link.

.. image:: ../../../tests/robotframework/screenshots/archive_header.png
   :class: sosse-screenshot

When the :doc:`Crawl Policy <../crawl/policies>` has ``🔖 Archive content`` or ``📷 Take screenshots`` enabled,
the archive page shows the rendered content and links to other indexed pages can be clicked:

.. image:: ../../../tests/robotframework/screenshots/archive_screenshot.png
   :class: sosse-screenshot

The ``✏️ Text`` links to the text version of the page. The ``📚 Word weights`` shows the weight of
stemmed words in the page, these are used to calculate the score of the page in the :doc:`search results <search>`.
