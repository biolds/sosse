Documents
=========

The list of all indexed documents can be reached from the :doc:`../admin_ui`, by clicking on ``Documents``.

.. image:: ../../tests/robotframework/screenshots/documents_list.png
   :class: sosse-screenshot
   :scale: 50%

The document page contains fields about the crawl status of the page.

Status
""""""

Shows if the document triggered an error during its last crawl.

Error
"""""

The error tat was triggered during last crawl if any.

Crawl DT
""""""""

The interval before the next recrawl of the document.

Recursion remaining
"""""""""""""""""""

The number of recursion level remaining, when the matching policy crawls :ref:`Depending on depth <crawl_depth_params>`.

Too many redirects
""""""""""""""""""

Indicates if the page was not crawled due to too many redirection. The limit can be set in the :ref:`configuration file <conf_option_max_redirects>`.
