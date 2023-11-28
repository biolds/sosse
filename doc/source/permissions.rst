User management
===============

User management and group edition can be done from the :doc:`../admin_ui`, by clicking on ``Users`` or ``Groups``.
Thanks to the `Django framework <https://www.djangoproject.com/>`_, fine-grained permissions can be defined by group and by user. 

.. image:: ../../tests/robotframework/screenshots/user_management.png
   :class: sosse-screenshot

The permission are set by type of objects modifiable through the :doc:`admin_ui`. Some of these permissions also give access to other
parts of the user interface:

- ``Can add document``: gives access to the :doc:`🌐 Crawl a new URL <crawl/add_to_queue>` page
- ``Can change document``: gives access to the document actions (``Crawl now``, ``Remove from crawl queue``, ``Convert screens to jpeg``)
- ``Can add crawler stats``: gives access to the :doc:`✔ Crawl status <crawl/status>` page
- ``Can change crawler stats``: gives access to the ``Pause`` and ``Resume`` crawler button in the :doc:`✔ Crawl status  <crawl/status>` page
