Documents
=========

The list of all indexed documents can be reached from the :doc:`../admin_ui`, by clicking on ``Documents``. Regular expressions can be used in the search bar to match URLs or page titles.

.. image:: ../../tests/robotframework/screenshots/documents_list.png
   :class: sosse-screenshot

The document page contains fields about the crawl status of the page:

Status
""""""

Shows if the document triggered an error during its last crawl.

.. _document_error:

Error
"""""

The error tat was triggered during last crawl if any.

Crawl DT
""""""""

The interval before the next recrawl of the document.

Recursion remaining
"""""""""""""""""""

The number of recursion level remaining, when the matching policy crawls :ref:`Depending on depth <recursion_depth_params>`.

Rejected by robots.txt
""""""""""""""""""""""

This indicates if the URL was not crawled due to a ``robots.txt`` rule. If necessary the ``robots.txt`` can be ignored in
the :ref:`Domain settings <domain_ignore_robots>`.

Too many redirects
""""""""""""""""""

Indicates if the page was not crawled due to too many redirection. The limit can be set in the :ref:`configuration file <conf_option_max_redirects>`.

.. _document_show_on_homepage:

Show on homepage
""""""""""""""""

When the :ref:`browsable home option <conf_option_browsable_home>` is enabled, this parameter can switch availability of the document from the homepage. (See :doc:`archive`)

Hidden
""""""

The document does not appear in search results.
