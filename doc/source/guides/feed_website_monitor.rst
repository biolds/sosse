Monitor Websites for Specific Keywords
======================================

Sosse can be used to receive updates when a new page containing a specific
keyword is published on a website. This
functionality can be applied to a variety of use cases, such as monitoring
merchant websites for promotional offers, or
watching for event announcements.

For this use case, we'll monitor a website for common functional errors, like
missing pages, server crashes, forbidden
access, and database issues, and generate an Atom feed of faulty pages.

Creating the Collections
---------------------------

Collections are essential for controlling how Sosse accesses and logs content
from websites. For more details, see
the :doc:`Collections <../crawl/collections>` documentation.

Create a collection for the website that we want to monitor, with the
parameters:

- In the ``⚡ Crawl`` tab, set ``Unlimited depth URL regex`` to
  ``^https://my.broken-website.com/.*`` to
  target the website.
- In the ``🔖 Archive`` tab, disable ``Archive content`` (as we don't need to
  archive the original feed).
- In the ``🕑 Recurrence`` tab, set ``Crawl frequency`` to ``Constant time``
  and clear the ``Recrawl dt max``
  field.

.. image:: ../../../tests/robotframework/screenshots/guide_feed_website_monitor_collections.png
   :class: sosse-screenshot

Start Crawling
--------------

To start crawling, go to the :doc:`Crawl a new URL <../crawl/new_url>` page and
enter the URL of the homepage:
``https://my.broken-website.com/``.

Check the parameters, then click ``Add to Crawl Queue``. Once confirmed, Sosse will begin
crawling and logging any pages that match
the regular expression from the Collection every day.

Generate Atom Feed
------------------

To get notified of errors, create a search with the following parameters:

- Sort: ``Last modified descending``. This ordering causes the feed to
  generate new entries for previously known pages
  whenever they are modified.
- Search options:

  - Action: ``Keep``
  - Field: ``Document``
  - Operator: ``Matching Regex``
  - Value::

      (Database Connection Failed|Internal Server Error|Not Found|Forbidden|
      Bad Gateway|Service Unavailable|Gateway Timeout|Request Timeout)

The pages in error can then be followed by subscribing to the
``Atom results feed`` (see :ref:`Atom feeds
<ui_atom_feeds>`).

.. image:: ../../../tests/robotframework/screenshots/guide_feed_website_monitor_error_search.png
   :class: sosse-screenshot

Additional Options
------------------

You may need to update the :doc:`Collection <../crawl/collections>` to use a
browser if the site relies on JavaScript or
requires authentication to access private areas. Additionally, it could be
useful to configure the :ref:`atom
feed <ui_atom_feeds>` to function while anonymous searches are disabled. Once
configured, you can integrate it with
services like `Zapier <https://zapier.com/>`_ or `IFTTT <https://ifttt.com/>`_
to trigger notifications whenever a new
error is detected.
