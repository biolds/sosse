Crawl Policies
==============

Policy matching
---------------

Crawl policies define which pages are indexed and how they are indexed. The policy list can be reached by clicking ``⚡ Crawl policies`` from the :doc:`../admin_ui`.

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_list.png
   :class: sosse-screenshot

When the crawler indexes a page or evaluates a link to queue it, it will find the best matching policy to know how to handle the link.
The policy with the longest ``URL regex`` matching is selected. On last resort, the default policy ``.*`` is selected.

You can see which policy would match by typing an URL in the search bar of the ``⚡ Crawl policies``, or in the ``🌐 Crawl a new URL`` page (see :doc:`add_to_queue`).

Indexing decision
-----------------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_decision.png
   :class: sosse-screenshot

URL regexp
""""""""""

The regexp matched against URL to crawl. The default ``.*`` policy's regexp cannot be modified.

Documents
"""""""""

Shows the URLs in the database that match the regexp.

.. _recursion_depth_params:

Recursion, recursion depth
""""""""""""""""""""""""""

``Recursion`` and ``Recursion depth`` parameters define which links to recurse into.

``Recursion`` can be one of:

* ``Crawl all pages``: URLs matching the policy will be crawled
* ``Depending on depth``: URLs matching the policy are crawled depending on the recursion level (see :doc:`recursion_depth`)
* ``Never crawl``: URLs matching the policy are not crawled unless they are queued manually (in this case, no recursion occurs)

``Recursion depth`` is only relevant when the ``Recursion`` is ``Crawl all pages`` and defines the recursion depth for links outside the policy. See :doc:`recursion_depth` for more explanations.

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

Hide documents
""""""""""""""

Documents indexed will be hidden from search results. The hidden state can later be changed from the :doc:`document's settings <../documents>`.

Remove nav elements
"""""""""""""""""""

This option removes HTML elements `<nav>`, `<header>` and `<footer>` before processing the page:

* ``From index``: words used inside navigation elements are not added to the search index, this is the default.
* ``From index and screenshots``: as above, also the elements are deleted before taking screenshots, this can be useful when websites are using sticky elements that follows scrolling.
* ``From index, screens and HTML snaps``: as above, but also removes the elements from the HTML snapshot.
* ``No``: the elements are not removed and are handled like regular elements.

Browser
-------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_browser.png
   :class: sosse-screenshot

.. _default_browse_params:

Default browse mode
"""""""""""""""""""

Can be one of:

* ``Detect``: the first time a domain is accessed, it is crawled with a browser and Python Requests. If the text content varies, it is assumed that the website is dynamic and the browser will be used for subsequent crawling of pages in this domain. If the text content is the same, Python Request will be used since it is faster. By default, the browser used is Chromium, this can be changed with the :ref:`default_browser option <conf_option_default_browser>`.
* ``Chromium``: Chromium is used.
* ``Firefox``: Firefox is used.
* ``Python Requests``: Python Requests is used.

.. _policy_create_thumbnails:

Create thumbnails
"""""""""""""""""

Make thumbnails of pages. These thumbnails are displayed in search results.

.. note::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

.. _policy_take_screenshot:

Take screenshots
""""""""""""""""

Enables taking screenshots of pages for offline use. When the option :ref:`Create thumbnails <policy_create_thumbnails>` is disabled, the screenshot is displayed in search results instead.

.. note::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

Screenshot format
"""""""""""""""""

Format of the image JPG or PNG.

.. note::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

.. _script_params:

Script
""""""

Javascript code to be executed in the context of the web pages when they have finished loading. This can be used to handle authentication, validate forms, remove headers, ...

For example, the following script could be used to click on a `GDPR <https://en.wikipedia.org/wiki/General_Data_Protection_Regulation>`_ compliance ``I agree`` button:

.. code-block:: javascript

   const BUTTON_TEXT = "I agree";
   const XPATH_PATTERN = `//*[contains(., "${BUTTON_TEXT}")]`;
   const button = document.evaluate(XPATH_PATTERN, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

   if (button && button.singleNodeValue) {
       button.singleNodeValue.click();
   }

In case the script triggers an error, further processing of the page is aborted and the error message is stored in the :ref:`document error field <document_error>`. It can be useful to use a tool such as `Tampermonkey <https://www.tampermonkey.net/>`_ to debug these kind of script.

.. note::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

.. _policy_html_snapshot:

HTML snapshot
-------------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_html_snapshot.png
   :class: sosse-screenshot

Snapshot html
"""""""""""""

This option enables capturing snapshots of crawled HTML pages and there related images, CSS, etc. it relies on for offline use.

A browser can be used to take the snapshot after dynamic content is loaded.

Snapshot exclude url re
"""""""""""""""""""""""

This field defines a regular expression of URL of related assets to skip downloading. For example, setting a regexp of ``png$`` would make the crawler
skip the download of URL ending with ``png``.

Snapshot exclude mime re
""""""""""""""""""""""""

This field defines a regular expression of mimetypes of related assets to skip saving, however files are still downloaded to determine there mimetype.
For example, setting a regexp of ``image/.*`` would make the crawler skip saving images.

Snapshot exclude element re
"""""""""""""""""""""""""""

This field defines a regular expression of HTML element of related assets to skip downloading. For example, setting a regexp of ``audio|video`` would make the crawler
skip the download of medias.

Recurrence
----------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_updates.png
   :class: sosse-screenshot

Crawl frequency, Recrawl dt
"""""""""""""""""""""""""""

How often pages should be reindexed:

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
