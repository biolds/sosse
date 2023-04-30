Crawl Policies
==============

Policy matching
---------------

Crawl policies define which pages are indexed and how they are indexed. The policy list can be reached by clicking ``Crawl policies`` from the :doc:`../admin_ui`.

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_list.png
   :class: sosse-screenshot
   :scale: 50%

When the crawler indexes a page or evaluates a link to queue it, it will find the best matching policy to know how to handle the link.
The policy with the longest ``URL regex`` matching is selected. On last resort, the default policy ``.*`` is selected.

You can see which policy would match by typing an URL in the search bar of the ``Crawl policies pages``, or in the ``Crawl a new URL`` page (see :doc:`add_to_queue`).

Indexing decision
-----------------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_decision.png
   :class: sosse-screenshot
   :scale: 50%

URL regexp
""""""""""

The regexp matched against URL to crawl. The default ``.*`` policy's regexp cannot be modified.

Documents
"""""""""

Shows the URLs in the database that match the regexp.

.. _crawl_depth_params:

Condition, Crawl depth
""""""""""""""""""""""

``Condition`` and ``Crawl depth`` parameters define which links to recurse into.

``Condition`` can be one of:

* ``Crawl all pages``: URLs matching the policy will be crawled
* ``Depending on depth``: URLs matching the policy are crawled depending on the recursion level (see :doc:`crawl_depth`)
* ``Never crawl``: URLS matching the policy are not crawled unless they are queued manually (in this case, no recursion occurs)

``Crawl depth`` is only relevant when the ``Condition`` is ``Crawl all pages`` and defines the recursion depth for links outside the policy. See :doc:`crawl_depth` for more explanations.

Mimetype regex
""""""""""""""

The mimetype of pages must match the regexp to be crawled.

Index URL parameters
""""""""""""""""""""

When enabled, URLs are stored with URLs parameters. Otherwise, URLs parameters are removed before indexing.
This can be useful if some parameters are random, change sorting or filtering, ...

Store extern links
""""""""""""""""""

When enabled, links to non-indexed pages are stored.

Browser
-------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_browser.png
   :class: sosse-screenshot
   :scale: 50%

.. _default_browse_params:

Default browse mode
"""""""""""""""""""

Can be one of:

* ``Detect``: the first time a domain is accessed, it is crawled with both Chromium and Python Requests. If the text content varies, it is assumed that the website is dynamic and Chromium will be used for subsequent crawling of pages in this domain. If the text content is the same, Python Request will be used since it is faster.
* ``Chromium``: Chromium is used.
* ``Python Requests``: Python Requests is used.

Take screenshots
""""""""""""""""

Enables taking screenshots of pages for offline use.

Screenshot format
"""""""""""""""""

Format of the image JPG or PNG.

.. _script_params:

Script
""""""

Javascript code to be executed in the context of the web pages when they have finished loading. This can be used to handle authentication, validate forms, remove headers, ...

For example, the following script could be used to click on a `GDPR <https://en.wikipedia.org/wiki/General_Data_Protection_Regulation>`_ compliance ``I agree`` button:

.. code-block:: javascript

   const BUTTON_TEXT = "I agree";
   const XPATH_PATTERN = `//*[text()="${BUTTON_TEXT}"]`;
   const button = document.evaluate(XPATH_PATTERN, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

   if (button && button.singleNodeValue) {
       button.singleNodeValue.click();
   }

In case the script triggers an error, further processing of the page is aborted and the error message is stored in the :ref:`document error field <document_error>`. It can be useful to use a tool such as `Tamperonkey <https://www.tampermonkey.net/>`_ to debug these kind of script.

Updates
-------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_updates.png
   :class: sosse-screenshot
   :scale: 50%

Crawl frequency, Recrawl dt
"""""""""""""""""""""""""""

How often pges should be reindexed:

* ``Once``: pages are not recrawled.
* ``Constant``: pages are recrawled every ``Recrawl dt min``.
* ``Adaptive``: pages recrawled more often when they change. The interval between recrawls starts at ``Recrawl dt min``. Then, when the page is recrawled the interval is multiplied by 2 if the content is unchanged, divided by 2 otherwise. The interval stays enclosed between ``Recrawl dt min`` and ``Recrawl dt max``.

Hash mode
"""""""""

Define how changes between recrawl are detected:

* ``Hash raw content``: raw text content is compared.
* ``Normalize numbers before``: numbers are replaced by 0s before comparing, it can be useful to ignore counters, clock changes, ...

.. _authentication_params:

Authentication
--------------

See :doc:`../authentication` for general guidelines on authentication.

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_auth.png
   :class: sosse-screenshot
   :scale: 50%

Login URL
"""""""""

If crawling a page matching the policy gets redirected to the ``Login URL``, the crawler will attempt to authenticate using the parameters definedbelow.

Form selector
"""""""""""""

CSS selector pointing to the authentication ``<form>`` element.

Authentication fields
"""""""""""""""""""""

This defines the ``<input>`` fields to fill in the form. The fields are matched by their ``name`` attribute and filled with the ``value``.
(hidden fields, like `CSRF <https://en.wikipedia.org/wiki/Cross-site_request_forgery>`_ preventing field, are automatically populated by the crawler)
