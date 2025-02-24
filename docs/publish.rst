.. _publish:

Publishing
==========

Publish Workflow
----------------

Publishing flow in Superdesk mainly consists of the next stages:

    - `Publish Producer`_
    - `Publish Exchange`_
    - `Publish Consumer`_

.. uml ::

    @startuml
    left to right direction

    actor Action
    component Producer
    component Exchange

    component "Consumer" as ConsumerA
    actor "Subscriber" as SubscriberA
    component "Consumer" as ConsumerB
    actor "Subscriber" as SubscriberB
    component "Consumer" as ConsumerC
    actor "Subscriber" as SubscriberC

    Action --> Producer
    Producer --> Exchange
    Exchange --> ConsumerA
    ConsumerA --> SubscriberA
    Exchange --> ConsumerB
    ConsumerB --> SubscriberB
    Exchange --> ConsumerC
    ConsumerC --> SubscriberC

    @enduml

Common Publishing Terms:
^^^^^^^^^^^^^^^^^^^^^^^^

* **PublishAction:** The initial action that starts a request to publish an item
* **PublishProducer:** The module that receives a PublishAction, collects data, validates it, and sends a PublishRequest to the PublishExchange
* **PublishRequest:** Data required by the PublishExchange to process a publish action
* **PublishExchange:** The module that receives a PublishRequest, performs filtering, formatting and routing to PublishConsumers
* **PublishRequestResponse:** The response from the PublishExchange after it receives a PublishRequest (to be used in response to a PublishAction)
* **PublishFormatter:** Code that converts the provided item into the designated format (JSON, XML, HTML etc)
* **PublishTask:** A single unit of work for the PublishConsumer to consume
* **PublishQueue:** A database resource used to store PublishTasks and their current state
* **PublishConsumer:** The module that receives a PublishTask and sends them to PublishTransmitter(s)
* **PublishTransmitter:** The code that pushed the data to Subscriber Destinations
* **Subscriber/Destination:** A database resource used to store configs for where to publish items to
* **Product:** A database resource used to group ContentFilters together, for matching against items
* **ContentFilter:** A database resource used to group FilterConditions together, for matching against items
* **FilterCondition:** A database resource for storing the raw content filters

Publish Producer
----------------

The producer's role is to collect the information from the PublishAction, preprocess the request and construct
a PublishRequest from it. This PublishRequest is then sent off to the PublishExchange for further processing.

A PublishProducer:

* Validates the PublishAction
* Populates certain fields (such as ``firstpublished``)

There are multiple types of PublishProducers:

- *publish*
- *correct*
- *kill*
- *unpublish*
- *takedown*
- *resend*

.. uml ::

    @startuml
    left to right direction

    actor "Web API" as WebAPI
    actor "Ingest Rule" as IngestRule
    actor "Macro" as Macro

    file "Publish\nAction" as PublishAction
    file "Publish\nRequest" as PublishRequest

    package "Publish Producer" {
        database DB
        file "Item\nto\npublish" as ItemToPublish
        component "Publish\nProducer" as Producer
    }

    component "Publish\nExchange" as Exchange

    WebAPI --> PublishAction
    IngestRule --> PublishAction
    Macro --> PublishAction

    PublishAction --> Producer

    DB -l-> ItemToPublish
    ItemToPublish -l-> Producer
    Producer --> PublishRequest
    PublishRequest --> Exchange

    @enduml

Publish Exchange
----------------

The "Publish Exchange" is the workhorse of the publishing system, it performs:

* Filtering - Find matching Subscribers to provided item
* Formatting - Format the item
* Routing - Route the item to Consumers

.. uml ::

    @startuml
    left to right direction

    file "Publish\nRequest" as PublishRequest
    file "Publish\nTask(s)" as PublishTask
    package "Publish Exchange" {
        rectangle "Filter Subscribers" as ExchangeFiltering
        rectangle "Format Items" as ExchangeFormatting
        rectangle "Route To Consumers" as ExchangeRouting
    }
    component "Consumer(s)" as Consumer

    PublishRequest --> ExchangeFiltering
    ExchangeFiltering -l-> ExchangeFormatting
    ExchangeFormatting -l-> ExchangeRouting

    ExchangeRouting --> PublishTask
    PublishTask --> Consumer

    @enduml

There are multiple different types of PublishExchanges, and the PublishExchangeFactory will route a PublishRequest
to the appropriate PublishExchange based on certain criteria (such as ContentType, Publish Operation).

In core there are the following PublishExchanges:

* BasicPublishExchange
* ContentPublishExchange
* ContentCorrectionExchange
* ContentKillExchange

.. note::
    This PublishExchange system allows for lots of flexibility. For example, we have the opportunity to create custom
    exchanges for customers which require a change in the publish workflow.

Filtering
^^^^^^^^^

-- TODO-ASYNC: Fill in details

Formatting
^^^^^^^^^^

-- TODO-ASYNC: Fill in details

Routing
^^^^^^^

The PublishExchange uses the Subscriber config to determine what PublishConsumer to use for the PublishTask.

If the Subscriber has the `async` flag turned on it will use the `AsyncioPublishConsumer`_, otherwise
it will use the `CeleryPublishConsumer`_ consumer.

.. note::
    Currently the routing is very basic, and has lots of room for improvement. It will allow us to add more
    configuration options on a Subscriber and/or Destination to help determine the Consumer to use. It is also
    possible that custom consumers can be created for customers which changes how the consumer works.


Publish Consumer
----------------

The PublishConsumer receives PublishTask(s) from the PublishExchange and transmits the item to Subscriber Destinations.

There are currently 2 types of PublishConsumers:

* AsyncioPublishConsumer
* CeleryPublishConsumer

AsyncioPublishConsumer
^^^^^^^^^^^^^^^^^^^^^^

This PublishConsumer uses Python's asyncio library to transmit items to their final destination.

Using the asyncio event loop, it allows to transmit multiple items at the same time without using Celery Tasks.

.. note::
    Currently this consumer is not effective, as the PublishTransmitters don't use asyncio network calls. \
    Until they are converted to use asyncio, only 1 item can effectively be transmitted at once.

CeleryPublishConsumer
^^^^^^^^^^^^^^^^^^^^^

This PublishConsumer uses Celery workers to transmit items to their final destination.

Internally it creates a Celery task for each destination, which then uses the AsyncioPublishConsumer to transmit them.

This consumer works much in the same way as the old transmit code (before the async project).


Resource Models
---------------

Subscriber Models
^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.types.subscribers.SubscribersResource()
    :member-order: bysource
    :members:
    :undoc-members:
    :exclude-members: model_config

.. autoclass:: superdesk.types.subscribers.SubscriberDestination()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.types.subscribers.SubscriberLastClosed()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.types.subscribers.SubscriberSequenceSettings()
    :member-order: bysource
    :members:
    :undoc-members:


Product Models
^^^^^^^^^^^^^^

.. autoclass:: superdesk.types.products.ProductsResource()
    :member-order: bysource
    :members:
    :undoc-members:
    :exclude-members: model_config

.. autoclass:: superdesk.types.products.ProductContentFilter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.types.products.ProductFilterType()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.types.products.ProductTypes()
    :member-order: bysource
    :members:
    :undoc-members:


Content Filter Models
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.types.content_filters.ContentFiltersResource()
    :member-order: bysource
    :members:
    :undoc-members:
    :exclude-members: model_config

.. autoclass:: superdesk.types.content_filters.ContentFilter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.types.content_filters.ContentFilterExpression()
    :member-order: bysource
    :members:
    :undoc-members:


Filter Condition Models
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: superdesk.types.filter_conditions.FilterConditionsResource()
    :member-order: bysource
    :members:
    :undoc-members:
    :exclude-members: model_config

.. autoclass:: superdesk.types.filter_conditions.FilterConditionFieldParam()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.types.filter_conditions.FilterConditionOperator()
    :member-order: bysource
    :members:
    :undoc-members:

TODO-ASYNC: Remove Old System
-----------------------------

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

.. autofunction:: superdesk.publish_async.commands.transmit

.. note:: | It's possible to start transmission manually:

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
