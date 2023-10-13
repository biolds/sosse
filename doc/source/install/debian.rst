Debian install
==============

SOSSE can be installed using the official Debian repository. To do so, first import its GPG key:

.. code-block:: shell

   apt update
   apt install -y curl gpg
   mkdir -p /etc/keyrings/
   curl http://piggledy.org/repo/apt/debian/public.gpg.key | gpg --dearmor > /etc/keyrings/piggledy.gpg

Then setup the repository:

.. code-block:: shell

   echo 'deb [signed-by=/etc/keyrings/piggledy.gpg] http://piggledy.org/repo/apt/debian bookworm main' > /etc/apt/sources.list.d/piggledy.list

The SOSSE package can then be installed with its dependencies:

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

To crawl pages with Firefox, it is required to install `Geckodriver <https://github.com/mozilla/geckodriver/>`_, with the command:

.. code-block:: shell

   curl -L https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz | tar -C /usr/local/bin -x -v -z -f -

.. note::
   A more recent Geckodriver may improve compatibily with the installed Firefox, though different versions have not been tested to work
   correctly with Sosse.

Next steps
----------

Congrats! The installation is done, you can now point your brwoser to the Nginx and log in with the user ``admin`` and the password ``admin``.
For more information about the configuration, you can follow the :doc:`../administration` pages.
