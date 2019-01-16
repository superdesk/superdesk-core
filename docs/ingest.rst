.. _ingest:

Ingest
======

.. module:: superdesk.io

With ingest you can import content into Superdesk. It supports multiple
formats and ways of delivery.

Ingest is running using celery, an update is triggered every 30s.

.. autofunction:: update_ingest

It iterates over all providers and check if provider is not closed, and
then checks ``last_updated`` time and schedule to realise if provider should
be updated now or later. If now it runs another celery task for each so it
can execute multiple updates in parallel.

.. autofunction:: update_provider

Once provider is updated, ``last_updated`` time is updated and it will ignore
that provider for some time according to ``schedule``.

Ingest Provider
---------------

Ingest provider specifies configuration for single ingest channel.

.. autoclass :: IngestProviderResource

Feeding Services
----------------

Handle transport protocols when ingesting.


.. module:: superdesk.io.feeding_services

.. autoclass:: superdesk.io.feeding_services.http_base_service.HTTPFeedingServiceBase

.. autoclass:: EmailFeedingService

.. autoclass:: FileFeedingService

.. autoclass:: FTPFeedingService

.. autoclass:: HTTPFeedingService

.. autoclass:: RSSFeedingService

.. autoclass:: apps.io.feeding_services.wufoo.WufooFeedingService

Add new Service
^^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.registry.register_feeding_service

Feed Parsers
------------

Parse items from services.

.. module:: superdesk.io.feed_parsers

.. autoclass:: ANPAFeedParser

.. autoclass:: IPTC7901FeedParser

.. autoclass:: NewsMLOneFeedParser

.. autoclass:: NewsMLTwoFeedParser

.. autoclass:: NITFFeedParser

.. autoclass:: EMailRFC822FeedParser

.. autoclass:: WENNFeedParser

.. autoclass:: DPAIPTC7901FeedParser

.. autoclass:: AFPNewsMLOneFeedParser

.. autoclass:: ScoopNewsMLTwoFeedParser

.. autoclass:: AP_ANPAFeedParser

.. autoclass:: PAFeedParser

Add new Parser
^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.registry.register_feed_parser

Add a Webhook
^^^^^^^^^^^^^

Webhook are a way to trigger ingestion without polling an ingest provider: the service do a POST HTTP request on a given URL to trigger the ingestion, resulting in resources saving and quicker ingestion.
Webhooks are using ``webhook`` endpoint. The service triggering the webhook must use this endpoint with 2 URLs parameters:

* ``provider_name`` which is the name of the provider to trigger
* ``auth`` which is an authentication key. This key is set in a ``WEBHOOK_[PROVIDER_NAME]_AUTH`` environment variable, when ``[PROVIDER_NAME]`` is the name of the provider in uppercase.

To activate the webhook, the ``WEBHOOK_[PROVIDER_NAME]_AUTH`` environment variable must be set.
Note that because ``auth`` parameter is used in request, HTTPS protocol should be used to avoid the key being sent unencrypted.
