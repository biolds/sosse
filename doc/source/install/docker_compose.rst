Running in Docker-compose
=========================

To run the latest version of Sosse with docker-compose, you need to download the latest version of the
``docker-compose.yml`` file from the Sosse repository in a dedicated directory:

.. code-block:: shell

   mkdir sosse
   cd sosse
   curl https://raw.githubusercontent.com/biolds/sosse/refs/heads/stable/docker-compose.yml > docker-compose.yml

Review its content, then run the following command to start Sosse:

.. code-block:: shell

   docker-compose up -d

By default, this would start an instance of Sosse on port 8005.

Environment Variable Configuration
----------------------------------

Sosse configurations can also be updated using environment variables. For detailed explanations of the available
configuration options, refer to the :doc:`../config_file`. After modifying the environment variables, it is necessary to
restart the Docker containers to apply the changes. Use the following commands to restart the containers:

.. code-block:: shell

   docker-compose down
   docker-compose up -d

Next steps
----------

You can now point your browser to connect to the port 8005 and log in with the user ``admin`` and the password
``admin``. For more information about the configuration, you can follow
:doc:`../guides/search` to start indexing documents, or explore other :doc:../guides'.
