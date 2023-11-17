Domain Settings
===============

Domain level parameters can be reached from the :doc:`../admin_ui`, by clicking on ``Domain settings``.

.. image:: ../../tests/robotframework/screenshots/domain_setting.png
   :class: sosse-screenshot

Domain settings are automatically created during crawling, but can also be updated manually or created manually.

Browse mode
"""""""""""

When the policy's :ref:`Default browse mode <default_browse_params>` is set to ``Detect``, the ``Browse mode`` option of the
domain define which browsing method to use. When its value is ``Detect``, the browsing mode is detected the next time the page
is accessed, and this option is switched to either ``Chromium``, ``Firefox``  or ``Python Requests``.

.. _domain_ignore_robots:

Ignore robots.txt
"""""""""""""""""

By default the crawler will honor the ``robots.txt`` 🤖 of the domain and follow its rules depending on the :ref:`User Agent <conf_option_user_agent>`.
When enabled, this option will ignore any ``robots.txt`` rule and crawl pages of the domain unconditionally.

Robots.txt status
"""""""""""""""""

One of:

* ``Unknown``: the file has not been processed yet
* ``Empty``: there is no ``robots.txt`` or it's empty
* ``Loaded``: the file has been successfully loaded

Robots.txt allow/disallow rules
"""""""""""""""""""""""""""""""

This contains the rules relevant to the crawlers :ref:`User Agent <conf_option_user_agent>`.
