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

.. autoclass:: EmailFeedingService

.. autoclass:: FileFeedingService

.. autoclass:: FTPFeedingService

.. autoclass:: HTTPFeedingService

.. autoclass:: RSSFeedingService

Add new Service
^^^^^^^^^^^^^^^

.. autofunction:: superdesk.io.register_feeding_service

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

.. autofunction:: superdesk.io.register_feed_parser
