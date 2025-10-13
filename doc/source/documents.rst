🔤 Documents
============

The list of all indexed documents can be reached from the :doc:`../admin_ui`, by clicking on ``Documents``. Regular
expressions can be used in the search bar to match URLs or page titles.

.. image:: ../../tests/robotframework/screenshots/documents_list.png
   :class: sosse-screenshot

Document detailed view
""""""""""""""""""""""

The document page contains fields about the crawl status of the page:

.. image:: ../../tests/robotframework/screenshots/documents_details.png
   :class: sosse-screenshot

Status
------

Shows if the document triggered an error during its last crawl.

.. _document_error:

Error
-----

The error that was triggered during last crawl if any.

Crawl DT
--------

The interval before the next recrawl of the document.

Recursion remaining
-------------------

The number of recursion levels remaining for this document when it was discovered through limited depth crawling (URLs
matching the :ref:`Limited depth URL regex <recursion_depth_params>`).

Rejected by robots.txt
----------------------

This indicates if the URL was not crawled due to a ``robots.txt`` rule. If necessary the ``robots.txt`` can be ignored
in the :ref:`Domain <domain_ignore_robots>`.

Too many redirects
------------------

Indicates if the page was not crawled due to too many redirection. The limit can be set in the
:ref:`configuration file <conf_option_max_redirects>`.

.. _document_show_on_homepage:

Show on homepage
----------------

When the :ref:`browsable home option <conf_option_browsable_home>` is enabled, this parameter can switch availability of
the document from the homepage. (See :doc:`guides/archive`)

Hidden
------

The document does not appear in search results.

Webhooks
--------

The Webhooks tab shows the result of :doc:`webhooks` that were run for this document.

.. image:: ../../tests/robotframework/screenshots/webhooks_result.png
   :class: sosse-screenshot

Metadata
--------

The Metadata tab shows associated metadata for the document. The metadata is stored in a JSON format and can be used to
add custom fields to the document. The metadata can be set using :ref:`Javascript execution <collection_script>` in
the browser context, or using the return value of the :doc:`webhooks`.

.. image:: ../../tests/robotframework/screenshots/metadata.png
   :class: sosse-screenshot


Document list view
""""""""""""""""""

Actions
-------

.. image:: ../../tests/robotframework/screenshots/documents_actions.png
   :class: sosse-screenshot

Using the actions dropdown, the following actions can be applied to the selected documents:

* ``Crawl now``: Triggers a crawl of the document as soon as a worker is available.
* ``Remove from crawl queue``: Removes the document from the crawl queue, it won't be processed unless
  manualy re-added.
* ``Convert screens to jpeg``: Converts the screenshots of the document to JPEG format.
* ``Switch hidden``: Toggles the hidden status of the document.
