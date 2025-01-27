Monitor Websites for Specific Keywords
======================================

SOSSE can be used to receive updates when a new page containing a specific keyword is published on a website. This
functionality can be applied to a variety of use cases, such as monitoring merchant websites for promotional offers, or
watching for event announcements.

For this use case, we’ll monitor a website for common functional errors, like missing pages, server crashes, forbidden
access, and database issues, and generate an Atom feed of faulty pages.

Modifying the Default Policy
----------------------------

Crawl policies are essential for controlling how SOSSE accesses and logs content from websites. For more details, see
the :doc:`Crawl Policies <../crawl/policies>` documentation. The default policy will crawl any link it finds, but we
will modify this behavior to ensure that only specified pages are crawled.

To modify the default policy, edit the ``(default)`` policy (see the :doc:`Crawl Policy <../crawl/policies>`), and set
the ``Recursion`` parameter to ``Never crawl`` instead of ``Crawl all pages``.

.. image:: ../../../tests/robotframework/screenshots/guide_feed_website_monitor_default_policy.png
   :class: sosse-screenshot

Creating the Crawl Policies
---------------------------

We add a policy for the website that we want to monitor, with the parameters:

- In the ``⚡ Crawl`` tab, use a regular expression ``^https://my.broken-website.com/.*`` to
  target the website. Set ``Thumbnail mode`` to ``No thumbnail`` (this disables the screenshot thumbnail,
  allowing the crawl to run without a browser for faster processing).
- In the ``🌍 Browser`` tab, set ``Default browse mode`` to ``Python Request``.
- In the ``🔖 Archive`` tab, disable ``Archive content`` (as we don't need to archive the original feed).
- In the ``🕑 Recurrence`` tab, set ``Crawl frequency`` to ``Constant time`` and clear the ``Recrawl dt max``
  field.

.. image:: ../../../tests/robotframework/screenshots/guide_feed_website_monitor_policies.png
   :class: sosse-screenshot

Start Crawling
--------------

To start crawling, go to the :doc:`Crawl a new URL <../crawl/new_url>` page and enter the URL of the homepage:
``https://my.broken-website.com/``.

Check the parameters, then click ``Confirm``. Once confirmed, SOSSE will begin crawling and logging any pages that match
the regular expression from the Crawl Policy every day.

Generate Atom Feed
------------------

To get notified of errors, create a search with the following parameters:

- Sort: ``Last modified descending``. This ordering causes the feed to generate new entries for previously known pages
  whenever they are modified.
- Search options:

  - Action: ``Keep``
  - Field: ``Document``
  - Operator: ``Matching Regex``
  - Value::

    (Database Connection Failed|Internal Server Error|Not Found|Forbidden|Bad Gateway|Service Unavailable|Gateway Timeout|Request Timeout)

The pages in error can then be followed by subscribing to the ``Atom results feed`` (see :ref:`Atom feeds
<ui_atom_feeds>`).

.. image:: ../../../tests/robotframework/screenshots/guide_feed_website_monitor_error_search.png
   :class: sosse-screenshot

Additional Options
------------------

You may need to update the :doc:`Crawl Policy <../crawl/policies>` to use a browser if the site relies on JavaScript or
requires authentication to access private areas. Additionally, it could be useful to configure the :ref:`atom
feed <ui_atom_feeds>` to function while anonymous searches are disabled. Once configured, you can integrate it with
services like `Zapier <https://zapier.com/>`_ or `IFTTT <https://ifttt.com/>`_ to trigger notifications whenever a new
error is detected.
