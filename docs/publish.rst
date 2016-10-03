Publishing
==========

Publish types
-------------

There are multiple types of publishing, which correcponds with item life cycle:

- *publish*
- *correct*
- *kill*

For each there is specific resource and service:

.. module:: apps.publish.content

.. class:: apps.publish.content.publish.ArchivePublishService

.. class:: apps.publish.content.correct.CorrectPublishService

.. class:: apps.publish.content.kill.KillPublishService

all inheriting from base publish service:

.. class:: apps.publish.content.common.BasePublishService

These in general handle validation and update item metadata.

Validation
----------

When publishing starts, it first validates the item based on its content profile definition
or in case content profile is missing it will get validators from db.
There are different validators for different content types (text, package, picture, etc)
and publish type.

Items in packages are also validated if were not published before. Package is considered not
valid if any of its item is not valid.

Schema definition
^^^^^^^^^^^^^^^^^

When using content profiles or validators, you specify a schema for each field like::

    "headline": {
        "type": "string",
        "required": true,
        "maxlength": 140,
        "minlength": 10
    }

More info about validation rules in `Eve docs <http://python-eve.org/config.html#schema-definition>`_.

Published
---------

When item is valid, it gets some metadata updates:

- ``state`` is set based on action
- ``_current_version`` is incremented
- ``version_creator`` is set to current user

These changes are saved to ``archive`` collection and ``published`` collection.
On client those items are not visible anymore in monitoring, only in desk output.

Publish queue
-------------

New items from ``published`` collection are further processed via async task:

.. autofunction:: apps.publish.enqueue.enqueue_published

Enqueueing is done via:

.. autoclass:: apps.publish.enqueue.enqueue_service.EnqueueService

    .. automethod:: enqueue_item

There it finds all subscribers that should recieve the item and if any it will format the item and queue transmission.

Supported output formats are:

.. toctree::
    :maxdepth: 1

    formatters/ninjs
    formatters/nitf
    formatters/newsml
    formatters/newsmlg2
    formatters/email


Transmission
------------

Last task is to send items to subscribers, that's handled via another async task:

.. autofunction:: superdesk.publish.transmit

This task runs every 10s.

There are different means of transport:

.. toctree::
    :maxdepth: 1

    transmitters/http-push
    transmitters/ftp
    transmitters/file
    transmitters/email
    transmitters/odbc
