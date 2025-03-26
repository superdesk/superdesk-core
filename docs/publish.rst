.. _publish:

Publishing
==========

.. contents:: Table of Contents
    :local:

Publish Workflow
----------------

Following is a high level overview of the main stages in publishing an item:

.. uml ::

    @startuml
    left to right direction

    actor Action
    component Producer
    component "Exchange\nFactory" as ExchangeFactory
    component Exchange

    component "Consumer" as ConsumerA
    actor "Subscriber" as SubscriberA
    component "Consumer" as ConsumerB
    actor "Subscriber" as SubscriberB
    component "Consumer" as ConsumerC
    actor "Subscriber" as SubscriberC

    Action --> Producer
    Producer --> ExchangeFactory
    ExchangeFactory --> Exchange
    Exchange --> ConsumerA
    ConsumerA --> SubscriberA
    Exchange --> ConsumerB
    ConsumerB --> SubscriberB
    Exchange --> ConsumerC
    ConsumerC --> SubscriberC

    @enduml

The publishing strategy used by the system can be configured in the :ref:`app settings <settings.publishing>`.

Common Publishing Terms:
^^^^^^^^^^^^^^^^^^^^^^^^

* **PublishAction:** The initial action that starts a request to publish an item
* **PublishProducer:** The module that receives a PublishAction, collects data, validates it, and sends a PublishRequest to the PublishExchange
* **PublishRequest:** Data required by the PublishExchange to process a publish action
* **PublishExchange:** The module that receives a PublishRequest, performs filtering, formatting and routing to PublishConsumers
* **PublishExchangeFactory:** Factory class for getting and interacting with PublishExchanges
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
* **PublishExchangeFilter:** The component of a PublishExchange that performs the subscriber filtering
* **PublishExchangeFormatter:** The component of a PublishExchange that performs the item formatting
* **PublishExchangeRouter:** The component of a PublishExchange that routes requests to consumers
* **PublishChannel:** An instance of a PublishExchange, with configured filter, formatter and router

Publish Exchange Factory
------------------------

The PublishExchangeFactory is the main interface used when interacting with the publishing system. It provides functionality
to:

* Register publish components from config
* Get publish components by name
* Get a PublishExchange based on a PublishRequest
* Send item(s) for publishing to a PublishExchange (based on the PublishChannel config)
* Process and send scheduled or pending content (from the ``published`` collection)
* Process pending publish queue items, sending them to a PublishExchange (based on the PublishChannel config)

The ``PUBLISH_EXCHANGE_FACTORY`` config is used to define what class to use, and defaults to
``"superdesk.publish_async.exchanges:DefaultPublishExchangeFactory"``.

To get an instance of the publish factory, use the following function:

.. autofunction:: superdesk.publish_async.get_exchange_factory

.. autoclass:: superdesk.publish_async.exchanges.exchange_factory.DefaultPublishExchangeFactory()
    :member-order: bysource
    :members:
    :undoc-members:

Publish Producer
----------------

The producer's role is to collect the information from the PublishAction, preprocess the request and construct
a PublishRequest from it. This PublishRequest is then sent off to the PublishExchange for further processing.

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
        component "Web API\nor\nIngest/Macro" as Producer
        file "Publish Request Response" as PublishRequestResponse
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
    Exchange -u-> PublishRequestResponse
    PublishRequestResponse -u-> PublishAction

    @enduml

There are 2 main types of PublishProducers, `Publish Actions from Web API requests`_ and
`Internal Publish Actions`_.

Publish Actions From Web API Requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These PublishActions come from a Web API request to publish an item. Each endpoint has it's own PublishProducer
class that handles the request:

* :class:`/\<api_prefix\>/archive/publish: ArchivePublishService <apps.publish.content.publish.ArchivePublishService>`
* :class:`/\<api_prefix\>/archive/correct: CorrectPublishService <apps.publish.content.correct.CorrectPublishService>`
* :class:`/\<api_prefix\>/archive/kill: KillPublishService <apps.publish.content.kill.KillPublishService>`
* :class:`/\<api_prefix\>/archive/unpublish: UnpublishService <apps.publish.unpublish.content.UnpublishService>`
* :class:`/\<api_prefix\>/archive/takedown: TakeDownPublishService <apps.publish.content.take_down.TakeDownPublishService>`
* :class:`/\<api_prefix\>/archive/resend: ResendService <apps.publish.content.resend.ResendService>`

With the exception of Resend, all inheriting from :class:`BasePublishService <apps.publish.content.common.BasePublishService>`

.. autoclass:: apps.publish.content.common.BasePublishService()

.. autoclass:: apps.publish.content.publish.ArchivePublishService()

.. autoclass:: apps.publish.content.correct.CorrectPublishService()

.. autoclass:: apps.publish.content.kill.KillPublishService()

.. autoclass:: apps.publish.content.unpublish.UnpublishService()

.. autoclass:: apps.publish.content.take_down.TakeDownPublishService()

.. autoclass:: apps.publish.content.resend.ResendService()

Internal Publish Actions
^^^^^^^^^^^^^^^^^^^^^^^^


**Ingest Rules:**

.. autoclass:: apps.rules.rule_handlers.DeskFetchPublishRoutingRuleHandler

**Macros:**

.. autofunction:: superdesk.macros.internal_destination_auto_publish.internal_destination_auto_publish

Validation
^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^

When item is valid, it gets some metadata updates:

- ``firstpublished`` is set to `publish_schedule` datetime if scheduled or `utcnow`
- ``operation`` is set to `"publish"`. Operation depends on publish types.
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
- ``pubstatus`` is set to `"usable"`. Pubstatus depends on publish types.
- ``expiry`` set item expiry
- ``word_count`` update word count

:meth:`apps.publish.content.publish.ArchivePublishService.on_update`

.. note:: If an item has associations, those are marked as used :meth:`ArchivePublishService._mark_media_item_as_used`

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
    database DB
    package "Publish Exchange" {
        rectangle "Filter Subscribers" as ExchangeFiltering
        rectangle "Format Items" as ExchangeFormatting
        file "PublishQueue Entry" as QueueEntry
        rectangle "Route To Consumers" as ExchangeRouting
    }
    component "Consumer(s)" as Consumer

    DB --> ExchangeFiltering
    PublishRequest --> ExchangeFiltering
    ExchangeFiltering -l-> ExchangeFormatting
    ExchangeFormatting -l-> QueueEntry
    QueueEntry --> DB
    QueueEntry -l-> ExchangeRouting

    ExchangeRouting --> PublishTask
    DB -> PublishTask
    PublishTask --> Consumer

    @enduml

There are multiple different types of PublishExchanges, and the PublishExchangeFactory will route a PublishRequest
to the appropriate PublishExchange based on certain criteria (such as ContentType, Publish Operation).

In core there are the following PublishExchanges:

* :class:`BasicPublishExchange <superdesk.publish_async.exchanges.base_exchange.BasicPublishExchange>`
* :class:`ContentPublishExchange <superdesk.publish_async.exchanges.content_exchange.ContentPublishExchange>`

The ``ContentPublishExchange`` exchange is used for publishing of content, as it knows how to handle the different
content databases, where as every other type (such as Event & Planning) will use ``BasicPublishExchange``.

.. note::
    This PublishExchange system allows for lots of flexibility. For example, we have the opportunity to create custom
    exchanges for customers which require a change in the publish workflow.

.. autoclass:: superdesk.publish_async.exchanges.base_exchange.BasicPublishExchange()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.publish_async.exchanges.content_exchange.ContentPublishExchange()
    :member-order: bysource
    :members:
    :undoc-members:


Publish Exchange Filter
^^^^^^^^^^^^^^^^^^^^^^^

The PublishExchangeFilter's role is to match the incoming item against Products to find the Subscribers to send
the item to.

Available PublishExchangeFilters:

* "default" -- :class:`BasePublishExchangeFilter <superdesk.publish_async.filters.base_exchange_filter.BasePublishExchangeFilter>`
* "content" -- :class:`ContentPublishExchangeFilter <superdesk.publish_async.filters.content_exchange_filter.ContentPublishExchangeFilter>`
* "content:corrected" -- :class:`CorrectedPublishExchangeFilter <superdesk.publish_async.filters.corrected_exchange_filter.CorrectedPublishExchangeFilter>`
* "content:killed" -- :class:`KilledPublishExchangeFilter <superdesk.publish_async.filters.killed_exchange_filter.KilledPublishExchangeFilter>`
* "resend" -- :class:`ResendPublishExchangeFilter <superdesk.publish_async.filters.resend_exchange_filter.ResendPublishExchangeFilter>`


.. autoclass:: superdesk.publish_async.filters.base_exchange_filter.BasePublishExchangeFilter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.publish_async.filters.content_exchange_filter.ContentPublishExchangeFilter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.publish_async.filters.corrected_exchange_filter.CorrectedPublishExchangeFilter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.publish_async.filters.killed_exchange_filter.KilledPublishExchangeFilter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.publish_async.filters.resend_exchange_filter.ResendPublishExchangeFilter()
    :member-order: bysource
    :members:
    :undoc-members:

Publish Exchange Formatter
^^^^^^^^^^^^^^^^^^^^^^^^^^

The PublishExchangeFormatter's role is to convert the incoming request to PublishQueue entries.
It does this by iterating over the matched Subscribers, and their destinations, and converts the item
using the configured `Output Formatters`_ for each destination. The PublishQueue entries
are then created and added into the database for use by PublishConsumers.

.. autoclass:: superdesk.publish_async.formatters.base_exchange_formatter.BasePublishExchangeFormatter()
    :member-order: bysource
    :members:
    :undoc-members:

Output Formatters
^^^^^^^^^^^^^^^^^

.. module:: superdesk.publish.formatters

Available core formatters:

* :class:`NINJSFormatter`
* :class:`NINJS2Formatter`
* :class:`NITFFormatter`
* :class:`NewsML12Formatter`
* :class:`NewsMLG2Formatter`
* :class:`EmailFormatter`
* :class:`NewsroomNinjsFormatter`
* :class:`IDMLFormatter`

.. autoclass:: NINJSFormatter

Superdesk NINJS Schema in :download:`JSON <superdesk-ninjs-schema.json>`.

.. autoclass:: NINJS2Formatter

.. autoclass:: FTPNinjsFormatter

.. autoclass:: NITFFormatter

.. autoclass:: NewsML12Formatter

.. autoclass:: NewsMLG2Formatter

.. autoclass:: EmailFormatter

.. autoclass:: NewsroomNinjsFormatter

.. autoclass:: IDMLFormatter

Publish Exchange Router
^^^^^^^^^^^^^^^^^^^^^^^

The PublishExchangeRouter's role is to route the PublishTasks/PublishQueue entries to the correct PublishConsumer,
based on the Subscriber config. Tasks will be grouped by it's Subscriber, so the consumer can process all
incoming requests per Subscriber.

The router will use the :meth:`get_exchange_factory().get_subscriber_consumer(subscriber) <superdesk.publish_async.exchanges.exchange_factory.DefaultPublishExchangeFactory.get_subscriber_consumer>` method from the PublishExchangeFactory
to get the correct Consumer based on the PublishTask's Subscriber.

The PublishConsumer used will be:

* `Asyncio Publish Consumer`_: If the Subscriber has the `async` flag turned on
* `Content API Consumer`_: If the Subscriber destination is the ContentAPI
* `Celery Publish Consumer`_: Otherwise the celery consumer will be used

.. note::
    Currently the routing is very basic, and has lots of room for improvement. It will allow us to add more
    configuration options on a Subscriber and/or Destination to help determine the Consumer to use. It is also
    possible that custom consumers can be created for customers which changes how the consumer works.

.. autoclass:: superdesk.publish_async.routers.asyncio_router.AsyncioPublishRouter()
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.publish_async.routers.celery_router.CeleryPublishRouter()
    :member-order: bysource
    :members:
    :undoc-members:


Publish Consumer
----------------

.. automodule:: superdesk.publish_async.consumers

The PublishConsumer's role is to receive PublishTask(s) for a single Subscriber, and transmit them to each
Destination within that Subscriber. The `Content Transmitters`_ are used to send the items.

.. uml ::

    @startuml
    left to right direction

    file "Publish\nTask(s)" as PublishTask
    component "Publish\nConsumer" as PublishConsumer
    file "Formatted Item" as FormattedItemA
    actor "Destination A" as DestinationA
    file "Formatted Item" as FormattedItemB
    actor "Destination B" as DestinationB
    file "Formatted Item" as FormattedItemC
    actor "Destination C" as DestinationC

    PublishTask --> PublishConsumer
    PublishConsumer --> FormattedItemA
    FormattedItemA --> DestinationA
    PublishConsumer --> FormattedItemB
    FormattedItemB --> DestinationB
    PublishConsumer --> FormattedItemC
    FormattedItemC --> DestinationC

    @enduml

There are currently 3 types of PublishConsumers:

* `AsyncioPublishConsumer <Asyncio Publish Consumer>`_
* `CeleryPublishConsumer <Celery Publish Consumer>`_
* `ContentApiPublishConsumer <Content API Consumer>`_

Asyncio Publish Consumer
^^^^^^^^^^^^^^^^^^^^^^^^

This PublishConsumer uses Python's asyncio library to transmit items to their final destination.

Using the asyncio event loop, it allows to transmit multiple items at the same time without using Celery Tasks.

.. note::
    Currently this consumer is not effective, as the PublishTransmitters don't use asyncio network calls. \
    Until they are converted to use asyncio, only 1 item can effectively be transmitted at once.

.. autoclass:: superdesk.publish_async.consumers.asyncio_consumer.AsyncioPublishConsumer()
    :member-order: bysource
    :members:
    :undoc-members:

Celery Publish Consumer
^^^^^^^^^^^^^^^^^^^^^^^

This PublishConsumer uses Celery workers to transmit items to their final destination.

Internally it creates a Celery task for each destination, which then uses the AsyncioPublishConsumer to transmit them.

This consumer works much in the same way as the old transmit code (before the async project).

.. autoclass:: superdesk.publish_async.consumers.celery_consumer.CeleryPublishConsumer()
    :member-order: bysource
    :members:
    :undoc-members:

Content API Consumer
^^^^^^^^^^^^^^^^^^^^

This PublishConsumer is specifically for publishing an item to the Content API. It calls internal code to
add the item into the Content API database directly.

.. autoclass:: superdesk.publish_async.consumers.content_api_consumer.ContentApiPublishConsumer()
    :member-order: bysource
    :members:
    :undoc-members:

Content Transmitters
^^^^^^^^^^^^^^^^^^^^

.. module:: superdesk.publish.transmitters

Available core transmitters:

* :class:`HTTPPushService`
* :class:`FTPPublishService`
* :class:`FilePublishService`
* :class:`EmailPublishService`
* :class:`ODBCPublishService`
* :class:`AmazonSQSFIFOPublishService`
* :class:`IMatricsTransmitter`

.. autoclass:: HTTPPushService

.. autoclass:: FTPPublishService

.. autoclass:: FilePublishService

.. autoclass:: EmailPublishService

.. autoclass:: ODBCPublishService

.. autoclass:: AmazonSQSFIFOPublishService

.. autoclass:: IMatricsTransmitter

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
