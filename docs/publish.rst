.. _publish:

Publishing
==========

Publish types
-------------

There are multiple types of publishing, which corresponds with item life cycle:

- *publish*
- *correct*
- *kill*
- *unpublish*
- *takedown*

For each there is specific resource and service:

.. module:: apps.publish.content

.. class:: apps.publish.content.publish.ArchivePublishService

.. class:: apps.publish.content.correct.CorrectPublishService

.. class:: apps.publish.content.kill.KillPublishService

.. class:: apps.publish.content.unpublish.UnpublishService

.. class:: apps.publish.content.take_down.TakeDownPublishService

all inheriting from base publish service

.. class:: apps.publish.content.common.BasePublishService

These in general handle validation and update item metadata.

Main steps
----------

Publishing flow in Superdesk mainly consists of the next stages:
    - [API] `validation`_
    - [API] `item metadata update`_
    - [API] `save item for enqueue`_
    - [CELERY] `processing`_
    - [CELERY] `transmission`_

Small diagram showing a publishing flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. uml::

    @startuml
    actor CLIENT
    participant API
    database DB
    participant CELERY
    CLIENT -> API : Publish
    API -[#green]> API : Validation
    API -[#green]> API : Item metadata update
    API -> DB : Save item for enqueue
    DB -[#green]> DB : Saved to **archive**
    DB -[#green]> DB : Saved to **published**
    DB <-[#blue]>o CELERY : Items from **published** are enqueued
    CELERY -[#green]> CELERY : Process queued items\n**apps.publish.enqueue.EnqueueContent**
    CELERY -> DB : Save result item into **publish_queue**
    DB <-[#blue]>o CELERY : Items from **publish_queue** are enqueued
    CELERY -[#green]> CELERY : Transmit queued items\n**superdesk.publish.transmit**
    @enduml

.. note:: In sections below ``ArchivePublishService`` will be used as an example reference.

Validation
----------

When publishing starts, it first validates the item based on its content profile definition
or in case content profile is missing it will get validators from db.
There are different validators for different content types (text, package, picture, etc)
and publish type.

:meth:`apps.publish.content.publish.ArchivePublishService._validate`

.. note:: :meth:`apps.validate.validate.ValidateService` is used for item validation


After the item is validated, associated items are validated to ensure that none of them are locked, killed, spiked, or recalled.

:meth:`apps.publish.content.publish.ArchivePublishService._validate_associated_items`


Items in packages are also validated if were not published before. Package is considered not
valid if any of its item is not valid.

:meth:`apps.publish.content.publish.ArchivePublishService._validate_package`

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


Item metadata update
--------------------

When item is valid, it gets some metadata updates:

- ``firstpublished`` is set to `publish_schedule` datetime if scheduled or `utcnow`
- ``operation`` is set to `"publish"`. Operation depends on `publish types`_.
    | This value defines which enqueue service will be used to enqueue an item.

    Enqueue services::

        enqueue_services = {
            ITEM_PUBLISH: EnqueuePublishedService(),
            ITEM_CORRECT: EnqueueCorrectedService(),
            ITEM_KILL: EnqueueKilledService(),
            ITEM_TAKEDOWN: EnqueueKilledService(published_state=CONTENT_STATE.RECALLED),
            ITEM_UNPUBLISH: EnqueueKilledService(published_state=CONTENT_STATE.UNPUBLISHED),
        }

- ``state`` is set based on action
- ``_current_version`` is incremented
- ``version_creator`` is set to current user
- ``pubstatus`` is set to `"usable"`. Pubstatus depends on `publish types`_.
- ``expiry`` set item expiry
- ``word_count`` update word count

:meth:`apps.publish.content.publish.ArchivePublishService.on_update`

.. note:: If an item has associations, those are marked as used :meth:`ArchivePublishService._mark_media_item_as_used`

Save item for enqueue
---------------------

These changes are saved to ``archive`` collection and ``published`` collection.

.. note:: | After item is saved to ``published`` collection,
    | :meth:`apps.publish.enqueue.enqueue_published.apply_async` is executed immediately.
    | **Celery beat also runs this task every 10 seconds**

Client is notified that item is published via ``item:publish`` push notification.
On client those items are not visible anymore in monitoring, only in desk output.

If there any updates to associated items and ``PUBLISH_ASSOCIATED_ITEMS`` is true
then publish the associated items.

:meth:`apps.publish.content.common.BasePublishService._publish_associated_items`

Processing
----------

.. module:: apps.publish.enqueue

New items from ``published`` collection are further processed via async task:

.. autofunction:: enqueue_published

which runs :meth:`apps.publish.enqueue.EnqueueContent` command.

.. note:: | It's possible to run this command manually using:

    ``python manage.py publish:enqueue``

Enqueueing is done via:

.. module:: apps.publish.enqueue.enqueue_service

.. autoclass:: EnqueueService

    .. automethod:: enqueue_item

| All items with queue state: "pending" that are not scheduled or scheduled time has lapsed are quiried for processing.
| ``item['operation']`` which was set at `item metadata update`_ step, defines an enqueue service.

There are a lot of actions happen in ``EnqueueService``:
    - get the subscribers:
        - get all active subscribers
        - filter the subscriber list based on the publish filter and global filters (if configured)
    - queue the content for subscribers ``EnqueueService.queue_transmission``:
        - get formatter
        - format item
        - save result item into `publish_queue`
    - sends notification if no formatter has found for any of the formats configured in subscriber
    - publish item to content API if configured

.. note:: Rewrites are sent to subscribers that received the original item or the previous rewrite.


Output Formatters
-----------------

.. module:: superdesk.publish.formatters

.. autoclass:: NINJSFormatter

Superdesk NINJS Schema in :download:`JSON <superdesk-ninjs-schema.json>`.

.. autoclass:: NINJS2Formatter

.. autoclass:: FTPNinjsFormatter

.. autoclass:: NITFFormatter

.. autoclass:: NewsML12Formatter

.. autoclass:: NewsMLG2Formatter

.. autoclass:: EmailFormatter

.. autoclass:: NITFFormatter

.. autoclass:: NewsroomNinjsFormatter

.. autoclass:: IDMLFormatter


Transmission
------------

Last task is to send items to subscribers, that's handled via another async task:

.. autofunction:: superdesk.publish.transmit

.. note:: | It's possible to start transmition manually:

    ``python manage.py publish:transmit``

This task runs every 10s.

Content Transmitters
--------------------

.. module:: superdesk.publish.transmitters

.. autoclass:: HTTPPushService

.. autoclass:: FTPPublishService

.. autoclass:: FilePublishService

.. autoclass:: EmailPublishService

.. autoclass:: ODBCPublishService
