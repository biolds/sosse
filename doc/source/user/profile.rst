Profile
===========

To reach the Profile user interface, click the |user_menu_button| button, then select ``Profile``.

.. |user_menu_button| image:: ../../../tests/robotframework/screenshots/user_menu_button.png
   :class: sosse-inline-screenshot

.. image:: ../../../tests/robotframework/screenshots/profile.png
   :class: sosse-screenshot

Profile data is stored in the browser's
`Local storage <https://en.wikipedia.org/wiki/Web_storage#Local_and_session_storage>`_, so they are not shared across
users, devices, or browsers.

Theme
-----

The theme option lets you choose light theme, dark theme or let it switch automatically depending on the browser
configuration.

Search terms parsing language
-----------------------------

This defines the default language used to read the search terms typed in the search bar. Sosse uses
`PostgreSQL's Full Text Search <https://www.postgresql.org/docs/current/textsearch-intro.html>`_ feature which uses
this parameter to make searches more intelligent than simple word matches.

Results by page
---------------

The number of search result displayed in one page.

.. _pref_principal_link:

Search result main links point to the archive
---------------------------------------------

When enabled, search result links point to the :doc:`archive versions <archive>` of pages. ``source`` links are
displayed to access original websites.

When disabled, search result links point to original websites. ``archive`` links are displayed to access
:doc:`archive versions <archive>`.

.. _pref_online_mode:

Online mode
-----------

When :ref:`Online detection <online_detection>` is set up, searching locally or online can be overridden.

.. image:: ../../../tests/robotframework/screenshots/online_mode.png
   :class: sosse-screenshot

Next to the user menu a dot displays the status of the online mode:

.. image:: ../../../tests/robotframework/screenshots/online_mode_status.png
   :class: sosse-screenshot

* Green for online
* Orange for offline
* Purple when ``Force online`` is selected
* Blue when ``Force local`` is selected
