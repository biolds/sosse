Dealing with Captchas
=====================

User agent
----------

By default, the crawlers send HTTP requests with a ``SOSSE`` `User agent HTTP header <https://en.wikipedia.org/wiki/User-Agent_header>`_
this can sometime lead websites to flag the crawler as a robot and display a Captcha.
To mitigate this, SOSSE can use the `Fake user-agent <https://github.com/fake-useragent/fake-useragent>`_ library to simulate a real
browser user agent. This can be achieved with the following options in the configuration file:

* :ref:`user_agent<conf_option_user_agent>`: uncomment the option and make it empty
* :ref:`fake_user_agent_browser<conf_option_fake_user_agent_browser>`, :ref:`fake_user_agent_os<conf_option_fake_user_agent_os>`, :ref:`fake_user_agent_platform<conf_option_fake_user_agent_platform>`: these control how the user agent is generated.
  It's probably best to set the ``fake_user_agent_platform`` to ``pc`` as some website may change there rendering on mobile platforms.

Cookies
-------

The captcha can be manually validated in a browser, then cookies can be exported and imported in SOSSE, see the :doc:`Cookies<../cookies>` documentation.
