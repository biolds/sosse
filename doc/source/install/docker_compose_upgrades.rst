Docker-compose upgrades
=======================

The Docker-compose version installed following the :doc:`docker_compose` documentation can be upgraded by running:

.. code-block:: shell

   docker-compose pull
   docker compose down
   docker compose up -d --force-recreate

It is recommended to make a backup of the database before upgrading.
