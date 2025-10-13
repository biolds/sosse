Debian install
==============

Sosse can be installed using the official Debian repository. To do so, first import its GPG key:

.. code-block:: shell

   apt update
   apt install -y curl gpg
   mkdir -p /etc/keyrings/
   curl https://piggledy.org/repo/apt/debian/public.gpg.key | gpg --dearmor > /etc/keyrings/piggledy.gpg

Then setup the repository:

.. code-block:: shell

   nano /etc/apt/sources.list.d/piggledy.sources

.. code-block:: default

   Types: deb
   URIs: https://piggledy.org/repo/apt/debian
   Suites: trixie
   Components: main
   Signed-By: /etc/keyrings/piggledy.gpg

.. note::

   On Debian Bookworm, you can configure the repository with:

   .. code-block:: shell

      echo 'deb [signed-by=/etc/keyrings/piggledy.gpg] http://piggledy.org/repo/apt/debian bookworm main' > /etc/apt/sources.list.d/piggledy.list

The Sosse package can then be installed with its dependencies:

.. code-block:: shell

   apt update
   apt install -y sosse

Database setup
--------------

.. include:: database_debian_generated.rst

Daemons setup
-------------

And then enable the daemons and start them:

.. code-block:: shell

   systemctl enable sosse-uwsgi
   systemctl enable sosse-crawler
   systemctl start sosse-uwsgi
   systemctl start sosse-crawler

Nginx site
----------

After installing the package, the Nginx site needs to be enabled with:

.. code-block:: shell

   rm -f /etc/nginx/sites-enabled/default
   ln -s /etc/nginx/sites-available/sosse.conf /etc/nginx/sites-enabled/
   systemctl restart nginx

Geckodriver setup (optional)
----------------------------

To crawl pages with Firefox, it is required to install `Geckodriver <https://github.com/mozilla/geckodriver/>`_, with
the command:

.. code-block:: shell

   curl -L https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz | tar -C /usr/local/bin -x -v -z -f -

.. note::
   A more recent Geckodriver may improve compatibily with the installed Firefox, though different versions have not been tested to work
   correctly with Sosse.

.. note::
   On Debian Bookworm, use Geckodriver v0.35.0 instead:

   .. code-block:: shell

      curl -L https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz | tar -C /usr/local/bin -x -v -z -f -

Configuration Updates
---------------------

The Sosse configuration can be updated in the file located at `/etc/sosse/sosse.conf`. For detailed explanations of the
configuration options, refer to the :doc:`../config_file`. After modifying the configuration file, it is necessary to
restart the Sosse daemons to apply the changes. Use the following commands to restart the daemons:

.. code-block:: shell

   systemctl restart sosse-crawler
   systemctl restart sosse-uwsgi

Next steps
----------

Congrats! The installation is done, you can now point your browser to the Nginx and log in with the user ``admin`` and
the password ``admin``. For more information about the configuration, you can follow
:doc:`../guides/search` to start indexing documents, or explore other :doc:../guides'.
