Running in Docker
=================

The latest stable version of SOSSE can be run in docker with the command:

.. code-block:: shell

   docker run -p 8005:80 --mount source=sosse_postgres,destination=/var/lib/postgresql \
                         --mount source=sosse_var,destination=/var/lib/sosse biolds/sosse:latest

This would start an instance of SOSSE on port 8005, and would persist data in the ``sosse_postgres`` and
``sosse_var`` `Docker volumes <https://docs.docker.com/storage/volumes/>`_.

You may also locally mount other directories to access their content, with the following flags:

* ``--volume $PWD/sosse-conf:/etc/sosse/``: mounting an empty directory as ``/etc/sosse/`` will create default configuration files in it. You can then edit them and restart Docker to make the changes effective.
* ``--volume $PWD/sosse-log:/var/log/sosse/``: mounting this directory would let you access log files.

Next steps
----------

You can now point your browser to connect to the port 8005 and log in with the user ``admin`` and the password ``admin``.
For more information about configuration, you can follow the :doc:`../administration` pages.
