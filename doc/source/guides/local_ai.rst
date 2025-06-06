Convert an RSS feed into Summaries Using a Webhook and Local AI
===============================================================

This guide shows how to configure Sosse to automatically summarize articles from RSS feeds using a local AI model.
It uses :doc:`../webhooks` and `Ollama <https://ollama.com/>`_, a Docker-based framework for running open-source LLMs
locally. It'll process articles from the `Segment <https://segment.com/>`_ blogs, but you can adapt it to any RSS feed.

.. note::
   This guide showcases the use of Ollama with the lightweight ``llama3.2`` model for demonstration purposes. However,
   you can explore other models like ``llama3``, ``mistral``, or ``gemma``. Feel free to substitute any supported model
   available in the `Ollama registry <https://ollama.com/library>`_.

.. image:: ../../../tests/robotframework/screenshots/guide_local_ai_results.png
   :alt: Screenshot showing summary metadata
   :class: sosse-screenshot

Set Up Ollama Locally with Docker
---------------------------------

First, install and start the Ollama server locally using Docker.

- **Run Ollama in Docker**::

     docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

- **Pull a model**::

     curl http://localhost:11434/api/pull -d '{ "name": "llama3.2" }'

You now have a local LLM endpoint running at ``http://localhost:11434`` with the selected model.

.. warning::
   This command runs a CPU-based model. For GPU support, check the `Ollama Docker image
   <https://hub.docker.com/r/ollama/ollama>`_ documentation for GPU setup.

.. note::
   You can test the functionality of the LLM by running a shell session with the following command::

     docker exec -it ollama ollama run llama3.2

Crawl Policies for RSS Feeds and Posts
--------------------------------------

Create a crawl policy to handle RSS feeds (refer to :doc:`../crawl/policies` for more details), navigate to ``⚡ Crawl
Policies`` in the admin panel, then create a new policy:

- ``URL regex``::

    ^https://segment\.com/blog/rss\.xml$

- Set ``Recursion depth`` to ``1`` to limit recursion to articles only.
- Under ``🕑 Recurrence``, specify the desired refresh interval, such as ``1 hour``.

Create a separate crawl policy to manage RSS posts:

- ``URL regex``::

    ^https://segment\.com/blog/

- Set ``Recursion`` to ``Depending on depth``, to have only articles referenced by the RSS feeds crawled.
- Under ``🕑 Recurrence``, set ``Crawl frequency`` to ``Once`` to avoid re-crawling the same articles.

Define the Webhook to Generate Summaries
----------------------------------------

Navigate to ``📡 Webhooks`` in the admin panel (refer to :doc:`../webhooks` for more details), and create a new webhook
to process the crawled articles:

- **Name**: ``Summarize Article``
- **URL**: ``http://localhost:11434/api/generate``
- Check **Overwrite document's fields with webhook response** : This ensures that the response generated by the
  webhook will replace the content in the document.
- **Path in JSON Response**: ``response``
- Check **Deserialize the response before updating the document** : This ensures that Sosse can parse the JSON content
  encapsulated within a text field in the response from Ollama.

- **JSON body template**::

    {
      "model": "llama3.2",
      "prompt": "Summarize the following text into 2-3 concise sentences.

        Output only the result as a JSON object:
        {\"content\": \"...\"}

        Text to summarize:\n${content}",
      "stream": false
    }

- **Method**: ``POST``
- Test the webhook by clicking the **Trigger** button at the bottom of the page, you should get a response like::

  {"model":"llama3.2","created_at":"2025-06-01T15:27:08.617590502Z","response":"{\"content\":\"Example\"}", ...

.. note::
   In case the webhook generates a ``Read timed out`` error, you can increase the timeout by modifying the
   :ref:`requests_timeout <conf_option_requests_timeout>` configuration option.

.. image:: ../../../tests/robotframework/screenshots/guide_local_ai_webhook_config.png
   :alt: Screenshot showing webhook configuration
   :class: sosse-screenshot

We instruct Ollama to summarize the article's content, provided in the ``${content}`` variable, and return the result as
a JSON object. The format aligns with the :doc:`../user/rest_api` response, allowing us to modify any fields in the
document.

You can now go back to the ``⚡ Crawl Policies`` page and select the newly created webhook under the
``📡 Webhooks`` tab.

Summarizing RSS Articles
------------------------

- Navigate to the :doc:`Crawl a new URL <../crawl/new_url>` page and paste the feed URL, such as::

   https://segment.com/blog/rss.xml

- Click **Confirm** to queue the crawl job.

Accessing Summaries
-------------------

From the homepage, you can perform a search to retrieve crawled articles along with their summaries:

- Expand the ``params`` panel:

  - Sort by ``First crawled descending`` to display the latest articles first.
  - Add a filter: ``Keep`` ``Linked by url`` ``Equal`` to ``https://segment.com/blog/rss.xml``.

- Submit the search to view the articles and their summaries.
- You can subscribe to a feed of these articles and summaries using `Atom feeds <ui_atom_feeds>`.

Related Resources
-----------------

- :doc:`data_extraction`
- :doc:`ai_api_processing`
- :doc:`../user/rest_api`
- https://ollama.com for model documentation and updates
