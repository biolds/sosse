Authentication handling
=======================

Authentication can be handled in various way described below:

Submitting forms
----------------

A lot of website are redirecting to a login page when accessing unauthorized content. SOSSE can detect this redirection, fill the login form and submit it before continuing to crawl. This method has the advantage of working on both Chromium/Firefox and Python Requests, and can handle credential expiration. It can be defined in the :ref:`⚡ Crawl policy <authentication_params>`.

Executing javascript
--------------------

When crawling pages with Chromium or Firefox, you can ran javascript code to handle any kind of authentication mechanism. See the ``⚡ Crawl policy`` :ref:`script parameter <script_params>`.

Cookie Edition
--------------

Session cookies can be directly set in the :doc:`cookies` interface.
