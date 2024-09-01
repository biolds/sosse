Configuration file reference
============================

SOSSE can be configured through the configuration file ``/etc/sosse/sosse.conf``. Configuration variables are grouped in 3 sections, depending
on which component they affect. Modyifing any of these option requires restarting the crawlers or the web interface.

.. note::
   Configuration options can also be set using environment variables by prefixing with ``SOSSE_``.
   For example, the proxy option of the crawler can be set by settings the ``SOSSE_PROXY`` environment variable.
   Envionment variable options have highher precedence than options from the configuration file.

.. include:: config_file_generated.rst
