📡 Webhooks
===========

Webhooks allow external services to be notified when a page is crawled. The webhook list can be accessed by clicking
**Webhooks** from the :doc:`admin_ui`.

.. image:: ../../tests/robotframework/screenshots/webhook_list.png
   :class: sosse-screenshot

When an event such as a new page discovery or a content change occurs, the corresponding webhook will be triggered,
sending an HTTP request to the specified URL. After creation, the webhook must be registered in
:doc:`Crawl Policies <crawl/policies>`. The execution result can be viewed on the relevant
:doc:`Document's page <documents>`.

Webhook Configuration
"""""""""""""""""""""

Webhook Name
------------

A unique name for the webhook, helping in its identification within the admin interface.

Trigger Condition
-----------------

Defines when the webhook should be triggered. Available options:

- **On content change** - Triggers when a document's content is modified.
- **On discovery** - Triggers when a new document is crawled for the first time.
- **On every crawl** - Triggers on every crawl and when manually triggered.
- **On content change or manual crawl** - Triggers when content changes or is manually triggered (default).

.. note::
   Webhooks for a document can also be manually triggered from the :doc:`document's settings <documents>`, regardless of
   the *Trigger Condition* parameter.

Update document with webhook response
-------------------------------------

When enabled, the 'Overwrite Document's Fields with Webhook Response' option allows the webhook response to update
specific fields in the indexed document. If the webhook returns data, those corresponding fields will be overwritten
with the new values.

Webhook URL
-----------

The endpoint URL where the webhook request will be sent.

HTTP Method
-----------

The HTTP method used for the request (e.g., GET, POST, PUT, DELETE).

Authentication
--------------

Basic authentication credentials for accessing the webhook URL:

- **Username** - The username for authentication (optional).
- **Password** - The password for authentication (optional).

Headers
-------

Additional headers to be included in the request, formatted as:

.. code-block::

   Header-Name: Value
   Another-Header: Value

Each header must be specified on a new line.

.. note::
   In addition to the provided headers, SOSSE sends the following headers:

   .. code-block::

      Accept: application/json
      Content-Type: application/json
      User-Agent: <User agent>

Body Template
-------------

A JSON template for the request body, which may include placeholders referencing document fields:

.. code-block:: json

   {
     "title": "New page crawled: $title",
     "content": "$content",
     "url": "$url"
   }

These placeholders will be replaced with actual document values when the webhook is triggered. The available fields
align with those returned by the :doc:`user/rest_api`.

Filtering Webhooks
------------------

Webhooks can be restricted to specific documents using the following filters:

- **Tags** - Triggers only for documents that have all specified tags, their children, or all documents if no tags are
  specified.
- **Mimetype regex** - Triggers only for documents whose mimetype matches this regex.
- **Title regex** - Triggers only for documents with a title matching this regex (one per line).
- **Content regex** - Triggers only for documents with content matching this regex (one per line).

Example: Discord Notification Webhook
"""""""""""""""""""""""""""""""""""""

A real-world application of webhooks is sending a notification to a Discord channel (using the
`Discord REST API <https://discord.com/developers/docs/intro>`_) when a new page is discovered. Below is an example
configuration for integrating with Discord:

Discord Webhook Setup
---------------------

- Create a new webhook in your Discord server by navigating to **Server Settings > Integrations > Webhooks**.
- Copy the webhook URL provided by Discord.
- Set **Webhook URL**: `<Your Discord Webhook URL>`

.. image:: ../../tests/robotframework/screenshots/webhook_add.png
   :class: sosse-screenshot

- Set **Trigger Condition**: ``On discovery``
- Set **Body Template**:

.. code-block:: json

   {
     "username": "Crawler Bot",
     "avatar_url": "[https://example.com/bot-avatar.png](https://example.com/bot-avatar.png)",
     "content": "A new page has been discovered: **$title**\nURL: $url"
   }

When a new document is discovered, this webhook will send a formatted message to the specified Discord channel,
notifying team members of the new content.
