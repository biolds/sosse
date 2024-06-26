Searches
========

.. image:: ../../../tests/robotframework/screenshots/search.png
   :class: sosse-screenshot

Making searches
---------------

SOSSE uses `PostgreSQL's Full Text Search <https://www.postgresql.org/docs/current/textsearch-intro.html>`_ to perform keyword based searches.
This makes the search bar behave like most search engine websites 🦡:

- Typing multiple space-separated keywords returns pages containing all of them.
- Separating search terms with ``OR`` returns pages containing one of them.
- Keywords enclosed in double-quotes match consecutive words.
- Using ``-`` in front of a search term removes matching pages from the result list.
- Parenthesis can be used to make complex queries and prioritize operators.

More search options are available when clicking on ``Params``:

.. image:: ../../../tests/robotframework/screenshots/extended_search.png
   :class: sosse-screenshot

- ``Language``: select document which detected language matches
- ``Sort``: sort order of matching documents
- ``Include hidden documents``: show hidden documents in results, requires the "Can change documents" permission

Below, more field can be added to perform exact text match as opposed to the search bar that has natural-language processing features (word stemming, diactric removal, ...).
Any number of extra filter can be added using the |plus_button| button. Each field in the filter is:

.. |plus_button| image:: ../../../tests/robotframework/screenshots/extended_search_plus_button.png
   :class: sosse-inline-screenshot

Function of the filter
""""""""""""""""""""""

- ``Keep``: pages matching the filter are displayed in the results
- ``Exclude``: pages matching the filter are removed from the results

Field
"""""

This defines against which field the keyword is matched:

- ``Document``: this matches against the ``Content``, the ``Title`` or the ``URL``
- ``Content``: the text content of the page
- ``Title``: the title of the page
- ``URL``: the URL of the page
- ``Mimetype``: the mimetype of the document
- ``Links to url``: returns documents containing links which target URLs matching the keyword
- ``Links to text``: returns documents containing links which text (the text of the link, not the text of the target document) matching the keyword
- ``Linked by url``: returns documents which are the target of the links of URLs matching the keyword
- ``Linked by text``: returns documents which are pointed by links whose text match the keyword

Operator
""""""""

This defines how the keyword is matched against the field:

- ``Containing``: this matches when the keyword is contained inside the field.
- ``Equal to``: this matches when the keyword is exactly to entire field.
- ``Matching Regexp``: matching is done using Posix regular expressions (see `PostgreSQL documention <https://www.postgresql.org/docs/current/functions-matching.html#POSIX-SYNTAX-DETAILS>`_ for details)

.. _ui_search_results:

Results
-------

.. image:: ../../../tests/robotframework/screenshots/search_result.png
   :class: sosse-screenshot

From top to bottom, left to right, the elements displayed are:

- the favicon of the page
- the title of the page, or its URL if it has no title
- the URL
- the score of the page for the provided search keywords from 0.0 to 1.0
- the language of the page
- the ``cached`` link to the cached version, or ``source`` link to the original page (depending on the :ref:`related option <pref_principal_link>`)

Word stats
----------

Clicking on the |stats_button| button, shows the top 100 most frequent words (after stemming) in the result webpages:

.. |stats_button| image:: ../../../tests/robotframework/screenshots/stats_button.png
   :class: sosse-inline-screenshot

.. image:: ../../../tests/robotframework/screenshots/word_stats.png
   :class: sosse-screenshot

.. _ui_atom_feeds:

Atom feeds
----------

The |atom_button| button, gives access to an `Atom feeds <https://en.wikipedia.org/wiki/Atom_rss>`_ for the current search terms ⚛:

.. |atom_button| image:: ../../../tests/robotframework/screenshots/atom_button.png
   :class: sosse-inline-screenshot

- ``Atom results feed`` has entries with links to the original website
- ``Atom cached feed`` has entries with links to the cached website

In case :ref:`anonymous searches <conf_option_anonymous_search>` are disabled, a :ref:`token <conf_option_atom_access_token>` can be defined to access
the Atom feed without authenticating. This is done by appending a ``token=<Atom access token>`` parameter to the Atom feeds URL.
