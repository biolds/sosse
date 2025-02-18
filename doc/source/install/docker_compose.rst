Running in Docker-compose
=========================

To run the latest version of SOSSE with docker-compose, you need to download the latest version of the
``docker-compose.yml`` file from the SOSSE repository in a dedicated directory:

.. code-block:: shell

   mkdir sosse
   cd sosse
   curl https://raw.githubusercontent.com/biolds/sosse/refs/heads/stable/docker-compose.yml > docker-compose.yml

Review its content, then run the following command to start SOSSE:

.. code-block:: shell

   docker-compose up -d

By default, this would start an instance of SOSSE on port 8005.

Next steps
----------

You can now point your browser to connect to the port 8005 and log in with the user ``admin`` and the password
``admin``. For more information about the configuration, you can follow the :doc:`../administration` pages,
or follow :doc:`../guides/search` to start indexing documents.
