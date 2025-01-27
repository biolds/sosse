Permissions
===========

Crawl Permissions
-----------------

User management and group editing can be done from the :doc:`../admin_ui`, by clicking on ``Users`` or ``Groups``.
Thanks to the `Django framework <https://www.djangoproject.com/>`_, fine-grained permissions can be defined by group and
by user.

.. image:: ../../tests/robotframework/screenshots/permissions.png
   :class: sosse-screenshot

Permissions are set by the type of objects that can be modified through the :doc:`admin_ui`. Some of these permissions
also grant access to other parts of the user interface:

- ``Can add document``: Grants access to the :doc:`🌐 Crawl a new URL <crawl/new_url>` page.
- ``Can change document``: Grants access to document actions such as ``Crawl now``, ``Remove from crawl queue``,
  ``Convert screens to JPEG``.
- ``Can view crawler stats``: Grants access to the :doc:`✔ Crawl queue <crawl/queue>` page and
  :doc:`🕷 Crawlers <crawl/crawlers>` page.
- ``Can change crawler stats``: Grants access to the ``Pause`` and ``Resume`` crawler buttons in the
  :doc:`✔ Crawl queue <crawl/queue>` page and :doc:`🕷 Crawlers <crawl/crawlers>` page.

Search Permissions
------------------

By default, search requires users to be authenticated, but :ref:`anonymous searches <conf_option_anonymous_search>`
can be enabled with the related option.
