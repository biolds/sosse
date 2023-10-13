Pip install
===========

Dependencies
------------

Before installing SOSSE, you'll need to manually install the following softwares:

- a web server supporting `WSGI <https://wsgi.readthedocs.io/en/latest/learn.html>`_ (the steps below explains how to setup `Nginx <https://nginx.org/>`_)
- a WSGI server (the steps below explains how to setup `uWSGI <https://uwsgi-docs.readthedocs.io/en/latest/>`_)
- `PostgreSQL <https://www.postgresql.org/>`_
- `Firefox <https://www.mozilla.org/firefox/>`_
- `Geckodriver <https://github.com/mozilla/geckodriver/>`_
- `Google Chromium <https://www.chromium.org/Home>`_
- `ChromeDriver <https://chromedriver.chromium.org/>`_

Package install
---------------

The installation can be done with the commands:

.. code-block:: shell

    virtualenv /opt/sosse-venv/
    /opt/sosse-venv/bin/pip install sosse

Default Configuration
---------------------

The default configuration and directories can be created with the commands:

.. code-block:: shell

   mkdir -p /run/sosse /var/log/sosse /var/www/.cache /var/www/.mozilla /var/lib/sosse/downloads /var/lib/sosse/screenshots /var/lib/sosse/html
   touch /var/log/sosse/crawler.log /var/log/sosse/debug.log /var/log/sosse/main.log /var/log/sosse/webserver.log
   chown -R www-data:www-data /run/sosse /var/lib/sosse /var/www/.cache /var/www/.mozilla /var/log/sosse
   mkdir /etc/sosse
   /opt/sosse-venv/bin/sosse-admin default_conf > /etc/sosse/sosse.conf

Static files
------------

Static files will be copied to their target location with the following command.

.. code-block:: shell

   /opt/sosse-venv/bin/sosse-admin collectstatic --noinput --clear

Database setup
--------------

.. include:: database_pip_generated.rst

WSGI server
-----------

You can install a WSGI server of your choice. If you wish to install `uWSGI <https://uwsgi-docs.readthedocs.io/en/latest/>`_, you can do:

.. code-block:: shell

   /opt/sosse-venv/bin/pip install uwsgi

And write the following config files:

.. code-block:: shell

   nano /etc/sosse/uwsgi.ini

.. literalinclude:: ../../../debian/uwsgi.ini

.. code-block:: shell

   nano /etc/sosse/uwsgi.params

.. literalinclude:: ../../../debian/uwsgi.params

After that, the server can be run in the background with:

.. code-block:: shell

   mkdir /var/log/uwsgi
   chown www-data:www-data /var/log/uwsgi
   /opt/sosse-venv/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini --logto /var/log/uwsgi/sosse.log &

File permissions
----------------

It's advised to restrict the permissions of the configuration files:

.. code-block:: shell

   chown -R root:www-data /etc/sosse
   chmod 750 /etc/sosse/
   chmod 640 /etc/sosse/*

Web server
----------

A web server like `Nginx <https://nginx.org/>`_ is required to relay requests to the WSGI server.
It's configuration should be done as follows:

.. code-block:: shell

   nano /etc/nginx/sites-available/sosse.conf

.. literalinclude:: ../../../debian/sosse.conf

Then it should be enabled, and `Nginx <https://nginx.org/>`_ started:

.. code-block:: shell

   rm -f /etc/nginx/sites-enabled/default
   ln -s /etc/nginx/sites-available/sosse.conf /etc/nginx/sites-enabled/
   nginx -g 'daemon on; master_process on;'

Crawlers
--------

Crawlers can now be started in the background with the command:

.. code-block:: shell

   sudo -u www-data /opt/sosse-venv/bin/sosse-admin crawl &

Next steps
----------

Congrats! The installation is done, you can now point your brwoser to the Nginx and log in with the user ``admin`` and the password ``admin``.
For more information about the configuration, you can follow the :doc:`../administration` pages.
