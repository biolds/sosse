External Search Engines
=======================

The list of :doc:`user/shortcuts` can be reached from the :doc:`../admin_ui`, by clicking on ``Search engines``.

.. image:: ../../tests/robotframework/screenshots/search_engines_list.png
   :class: sosse-screenshot

New search engines can be added manually, or using the :ref:`CLI <cli_load_se>` using an `Open Search Description <https://developer.mozilla.org/en-US/docs/Web/OpenSearch>`_ formatted file.

.. image:: ../../tests/robotframework/screenshots/search_engine.png
   :class: sosse-screenshot

In this form, the shortcut that will be used to redirect to the external search engine can be defined. If you add a search engine, please consider adding it to the list of `included search engines <https://gitlab.com/biolds1/sosse/-/blob/main/sosse/search_engines.json>`_ and opening a Pull request (also works on `Github <https://github.com/biolds/sosse/blob/main/sosse/search_engines.json>`_).
