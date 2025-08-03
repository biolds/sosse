🧩 Mime Handlers
================

Mime handler settings can be reached from the :doc:`admin_ui`, by clicking on
``Mime Handlers``.

.. image:: ../../tests/robotframework/screenshots/mime_handler_list.png
   :class: sosse-screenshot

Mime handlers are automatically executed during crawling when a document's MIME type
matches the handler's regex pattern. Built-in handlers are provided for common
document types, but custom handlers can also be created.

Mime handler detailed view
""""""""""""""""""""""""""

The mime handler detail page contains all configuration fields for the handler:

.. image:: ../../tests/robotframework/screenshots/mime_handler_detail.png
   :class: sosse-screenshot

Name
----

A unique descriptive name for the mime handler, used for identification within
the admin interface.

Description
-----------

Optional text field to describe what the handler does. This is particularly
useful for documenting custom handlers.

License
-------

License information for the script, such as "GPL-3.0" or "MIT". This field is
optional and mainly used for built-in handlers.

Enabled
-------

Controls whether this handler is active during crawling. Disabled handlers will
be ignored even if their MIME type pattern matches.

MIME Type Regex
---------------

One or more regular expressions (one per line) that define which MIME types this
handler should process. Examples:

* ``^application/pdf$`` - Matches PDF documents only
* ``^image/.*`` - Matches all image types
* ``^application/(msword|vnd\.openxmlformats-officedocument\.wordprocessingml\.document)$`` - Matches Word

Script
------

The shell script that processes the document. The script receives the file path
as the first argument and can extract content, metadata, or perform
transformations.

For built-in handlers, this field is displayed as a read-only textarea when the
handler is marked as builtin. Custom handlers allow full editing of the script
content.

The script is automatically saved to the filesystem and made executable when
the handler is saved.

Timeout
-------

Maximum execution time for the script in seconds (default: 30). If the script
takes longer than this timeout, it will be terminated to prevent blocking the
crawler.
