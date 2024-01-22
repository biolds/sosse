Recursive crawling
==================

SOSSE can crawl recursively all pages it finds, or the recursion level can be limited when crawling large websites or public sites.

No limit recursion
-------------------

Recursing with no limit is achieved by using a policy with a :ref:`Recursion <recursion_depth_params>` set to ``Crawl all pages`` (the default).

For example, a full domain can extracted with 2 policies:

* A policy for the domain with a ``URL regex`` that matches the domain, and ``Recursion`` set to ``Crawl all pages``

* A default policy (with the ``URL regex`` set to ``.*``) with a ``Recursion`` set to ``Never crawl``

Limited recursion
-----------------

Crawling pages up to a certain level can be simply achieved by setting the :ref:`Recursion <recursion_depth_params>` to ``Depending on depth`` and setting the ``Recursion depth`` when :doc:`queueing the initial URL <add_to_queue>`.

.. image:: ../../../tests/robotframework/screenshots/crawl_on_depth_add.png
   :class: sosse-screenshot

Partial limited recursion
-------------------------

A mixed approach is also possible, by setting a :ref:`Recursion <recursion_depth_params>` to ``Depending on depth`` in one policy, and setting it to ``Crawl all pages`` in an other and a positive ``Recursion depth``.

For example, one could crawl all Wikipedia, and crawl external links up to 2 levels with the following policies:

* A policy for Wikipedia, with ``Recursion depth`` of 2:

.. image:: ../../../tests/robotframework/screenshots/policy_all.png
   :class: sosse-screenshot

* A default policy with a ``Depending on depth`` condition:

.. image:: ../../../tests/robotframework/screenshots/policy_on_depth.png
   :class: sosse-screenshot
