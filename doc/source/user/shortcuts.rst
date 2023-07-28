External search engine shortcuts
================================

.. image:: ../../../tests/robotframework/screenshots/shortcut.png
   :class: sosse-screenshot

In the search bar, shortcuts can be used to search on external search engine. In the screenshot above, the search terms ``!b cats`` would redirect to the `Brave Search <https://search.brave.com/>`_ search engine, searching for ``cats`` 🐈.

The default list of shortcuts is available in the :doc:`shortcut_list` page, new search engines can be added in the :doc:`administration UI <../search_engines>`.

The special character (``!`` by default) used to trigger the shortcut can be modified in the :ref:`configuration <conf_option_search_shortcut_char>`.

It is possible to make SOSSE redirect to an external search engin by default by setting the option :ref:`default_search_redirect <conf_option_default_search_redirect>`. In this case SOSSE internal searches can still be reached using the shortcut defined by :ref:`sosse_shortcut <conf_option_sosse_shortcut>`.
