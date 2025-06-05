⚡ Crawl Policies
=================

Policy matching
---------------

Crawl policies define which pages are indexed and how they are indexed. The policy list can be reached by clicking
``⚡ Crawl policies`` from the :doc:`../admin_ui`.

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_list.png
   :class: sosse-screenshot

When the crawler indexes a page or evaluates a link to queue it, it will find the best matching policy to know how to
handle the link. The policy having the ``URL regex`` matching the longest part of the link URL is selected. On last
resort, the default policy ``(default)`` is selected.

You can see which policy would match by typing an URL in the search bar of the ``⚡ Crawl policies``, or in the
``🌐 Crawl a new URL`` page (see :doc:`new_url`).

⚡ Crawl
--------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_decision.png
   :class: sosse-screenshot

URL regex
"""""""""

The regex matched against URLs to crawl. Multiple regex can be set, one by line. Lines starting with a ``#`` are
treated as comments. The default ``(default)`` policy's regex cannot be modified.

Tags
""""

This field defines the tags to be added to documents matching the policy. Tags are used to group documents and can be
used to filter search results.

Documents
"""""""""

Shows the URLs in the database that match the regex.

.. _recursion_depth_params:

Recursion, recursion depth
""""""""""""""""""""""""""

``Recursion`` and ``Recursion depth`` parameters define which links to recurse into.

``Recursion`` can be one of:

* ``Crawl all pages``: URLs matching the policy will be crawled
* ``Depending on depth``: URLs matching the policy are crawled depending on the recursion level (see
  :doc:`recursion_depth`)
* ``Never crawl``: URLs matching the policy are not crawled unless they are queued manually (in this case, no recursion
  occurs)

``Recursion depth`` is only relevant when the ``Recursion`` is ``Crawl all pages`` and defines the recursion depth for
links outside the policy. See :doc:`recursion_depth` for more explanations.

Mimetype regex
""""""""""""""

The mimetype of pages must match the regex to be crawled.

Index URL parameters
""""""""""""""""""""

When enabled, URLs are stored with URLs parameters. Otherwise, URLs parameters are removed before indexing.
This can be useful if some parameters are random, change sorting or filtering, ...

Store extern links
""""""""""""""""""

When enabled, links to non-indexed pages are stored.

Hide documents
""""""""""""""

Documents indexed will be hidden from search results. The hidden state can later be changed from the
:doc:`document's settings <../documents>`.

Remove nav elements
"""""""""""""""""""

This option removes HTML elements `<nav>`, `<header>` and `<footer>` before processing the page:

* ``From index``: words used inside navigation elements are not added to the search index, this is the default.
* ``From index and screenshots``: as above, also the elements are deleted before taking screenshots, this can be useful
  when websites are using sticky elements that follows scrolling.
* ``From index, screens and HTML archive``: as above, but also removes the elements from the HTML archive.
* ``No``: the elements are not removed and are handled like regular elements.

Thumbnail mode
""""""""""""""

Defines the source for pages thumbnails displayed in the search results and home page:

* ``Page preview from metadata``: the thumbnail is extracted from the page metadata (using
  `Linkpreview <https://github.com/meyt/linkpreview>`_).
* ``Preview from meta, screenshot as fallback``: the thumbnail is extracted from metadata if available, a screenshot is
  taken otherwise.
* ``Take a screenshot``: a screenshot is used as thumbnail.
* ``No thumbnail``: no thumbnail is saved.

.. note::
   To take screenshot as thumbnails, the ``Default browse mode`` needs to be ``Chromium`` or ``Firefox``.

.. _policy_take_screenshot:

🌍 Browser
----------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_browser.png
   :class: sosse-screenshot

.. _default_browse_params:

Default browse mode
"""""""""""""""""""

Can be one of:

* ``Detect``: the first time a domain is accessed, it is crawled with a browser and Python Requests. If the text content
  varies, it is assumed that the website is dynamic and the browser will be used for subsequent crawling of pages in
  this domain. If the text content is the same, Python Request will be used since it is faster. By default, the browser
  used is Chromium, this can be changed with the :ref:`default_browser option <conf_option_default_browser>`.
* ``Chromium``: Chromium is used.
* ``Firefox``: Firefox is used.
* ``Python Requests``: Python Requests is used.

.. _policy_create_thumbnails:

Take screenshots
""""""""""""""""

Enables taking screenshots of pages for offline use. When the option
:ref:`Create thumbnails <policy_create_thumbnails>` is disabled, the screenshot is displayed in search results instead.

.. note::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

Screenshot format
"""""""""""""""""

Format of the image JPG or PNG.

.. note::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

.. _crawl_policy_script:

Script
""""""

Javascript code to be executed in the context of the web pages when they have finished loading. This can be used to
handle authentication, validate forms, remove headers, ...

For example, the following script could be used to click on a
`GDPR <https://en.wikipedia.org/wiki/General_Data_Protection_Regulation>`_ compliance ``I agree`` button:

.. code-block:: javascript

   const BUTTON_TEXT = "I agree";
   const XPATH_PATTERN = `//*[contains(., "${BUTTON_TEXT}")]`;
   const button = document.evaluate(XPATH_PATTERN, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

   if (button && button.singleNodeValue) {
       button.singleNodeValue.click();
   }

Or, this script scrolls to the bottom of the page (this can be useful in case some content loads when scrolling):

.. code-block:: javascript

   window.scrollTo(0, document.body.scrollHeight);

In case the script triggers an error, further processing of the page is aborted and the error message is stored in the
:ref:`document error field <document_error>`. It can be useful to use a tool such as
`Tampermonkey <https://www.tampermonkey.net/>`_ to debug these kind of script.

.. warning::
   This option requires the ``Default browse mode`` to be ``Chromium`` or ``Firefox`` in order to work.

.. note::
   The value returned by the script is used to update the document's data. This can be used to programmatically set the
   document's title, content, tags, etc. All fields of the document available in the :doc:`../user/rest_api` can be
   overwritten.

.. _policy_archive:

🔖 Archive
----------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_archive.png
   :class: sosse-screenshot

Archive content
"""""""""""""""

This option enables capturing snapshots of binary files, HTML pages and there related images, CSS, etc. it relies on for
offline use.

A browser can be used to take the snapshot after dynamic content is loaded.

Assets exclude URL regex
""""""""""""""""""""""""

This field defines a regular expression of URL of related assets to skip downloading. For example, setting a regex of
``png$`` would make the crawler skip the download of URL ending with ``png``.

Assets exclude mime regex
"""""""""""""""""""""""""

This field defines a regular expression of mimetypes of related assets to skip saving, however files are still
downloaded to determine there mimetype. For example, setting a regex of ``image/.*`` would make the crawler skip saving
images.

Assets exclude HTML regex
"""""""""""""""""""""""""

This field defines a regular expression of HTML element of related assets to skip downloading. For example, setting a
regex of ``audio|video`` would make the crawler skip the download of medias.

.. _crawl_policy_recurrence:

🕑 Recurrence
-------------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_updates.png
   :class: sosse-screenshot

Crawl frequency, Recrawl dt
"""""""""""""""""""""""""""

How often pages should be reindexed:

* ``Once``: pages are not recrawled.
* ``Constant``: pages are recrawled every ``Recrawl dt min``.
* ``Adaptive``: pages are recrawled more often when they change. The interval between recrawls starts at
  ``Recrawl dt min``. Then, when the page is recrawled the interval is multiplied by 2 if the content is unchanged,
  divided by 2 otherwise. The interval stays enclosed between ``Recrawl dt min`` and ``Recrawl dt max``.

Change detection
""""""""""""""""

Define how changes between recrawl are detected:

* ``Raw content``: raw text content is compared.
* ``Normalize numbers``: numbers are replaced by 0s before comparing, it can be useful to ignore counters, clock
  changes, ...

Condition
"""""""""

Defines when the page is reprocessed:

* ``On change only``: the content is reprocessed only when a change is detected.
* ``Always``: the content is reprocessed every time the page is recrawled. (this can be useful if
  the page only has pictures)
* ``On change or manual trigger``: the content is reprocessed when a change is detected or when the
  crawl was manually triggered.

.. _authentication_params:

🔒 Authentication
-----------------

See :doc:`../guides/authentication` for an example on authentication.

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_auth.png
   :class: sosse-screenshot

Login URL regex
"""""""""""""""

If crawling a page matching the policy gets redirected to an URL matching the ``Login URL regex``, the crawler will
attempt to authenticate using the parameters defined below.

Form selector
"""""""""""""

CSS selector pointing to the authentication ``<form>`` element.

Authentication fields
"""""""""""""""""""""

This defines the ``<input>`` fields to fill in the form. The fields are matched by their ``name`` attribute and filled
with the ``value``. (hidden fields, like `CSRF <https://en.wikipedia.org/wiki/Cross-site_request_forgery>`_ preventing
field, are automatically populated by the crawler)


Actions
-------

.. image:: ../../../tests/robotframework/screenshots/crawl_policy_actions.png
   :class: sosse-screenshot

Using the actions dropdown, the following actions can be applied to the selected crawl policies:

* ``Enable/Disable``: Toggles the Crawl Policy state.
* ``Duplicate``: Makes a copy of the Crawl Policy.
* ``Update doc tags``: Updates the tags of all documents matching the policy.
* ``Clear & update doc tags``: Clears the tags of all documents matching the policy and updates them.
