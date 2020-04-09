.. _publish:

Publishing
==========

Publish types
-------------

There are multiple types of publishing, which corresponds with item life cycle:

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

.. module:: apps.publish.enqueue

New items from ``published`` collection are further processed via async task:

.. autofunction:: enqueue_published

Enqueueing is done via:

.. module:: apps.publish.enqueue.enqueue_service

.. autoclass:: EnqueueService

    .. automethod:: enqueue_item

There it finds all subscribers that should receive the item and if any it will format the item and queue transmission.

Output Formatters
-----------------

.. module:: superdesk.publish.formatters

.. autoclass:: NINJSFormatter

Superdesk NINJS Schema in :download:`JSON <superdesk-ninjs-schema.json>`.

.. autoclass:: NINJS2Formatter

.. autoclass:: NITFFormatter

.. autoclass:: NewsML12Formatter

.. autoclass:: NewsMLG2Formatter

.. autoclass:: EmailFormatter

Transmission
------------

Last task is to send items to subscribers, that's handled via another async task:

.. autofunction:: superdesk.publish.transmit

This task runs every 10s.

Content Transmitters
--------------------

.. module:: superdesk.publish.transmitters

.. autoclass:: HTTPPushService

.. autoclass:: FTPPublishService

.. autoclass:: FilePublishService

.. autoclass:: EmailPublishService

.. autoclass:: ODBCPublishService
