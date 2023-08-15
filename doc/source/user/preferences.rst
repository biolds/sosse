Preferences
===========

To reach the Preferences user interface, click the |user_menu_button| button, then select ``Preferences``.

.. |user_menu_button| image:: ../../../tests/robotframework/screenshots/user_menu_button.png
   :class: sosse-inline-screenshot

.. image:: ../../../tests/robotframework/screenshots/preferences.png
   :class: sosse-screenshot

Preferences are stored in the browser's `Local storage <https://en.wikipedia.org/wiki/Web_storage#Local_and_session_storage>`_, so they are not shared accross users, devices, or browsers.

Search terms parsing language
-----------------------------

This defines the default language used to read the search terms typed in the search bar. SOSSE uses `PostgreSQL's Full Text Search <https://www.postgresql.org/docs/current/textsearch-intro.html>`_ feature which uses this parameter to make searches more intelligent than simple word matches.

Results by page
---------------

The number of search result displayed in one page.

.. _pref_principal_link:

Search result principal links point to cache
--------------------------------------------

When enabled, search result links point to the :doc:`cached versions <cached>` of pages. ``source`` links are displayed to access original websites.

When disabled, search result links point to original websites. ``cached`` links are displayed to access :doc:`cached versions <cached>`.
