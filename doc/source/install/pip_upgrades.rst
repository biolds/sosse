Pip upgrades
============

The Pip packages installed following the :doc:`pip` documentation can be upgraded by running:

.. code-block:: shell

   pip install --upgrade sosse

It is recommended to make a backup of the database before upgrading.

When the upgrade is done, the following commands need to be run to update the data:

.. code-block:: shell

   sosse-admin collectstatic --noinput --clear
   sosse-admin migrate
   sosse-admin update_se
