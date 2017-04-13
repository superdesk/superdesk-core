# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk IO"""

import logging

import superdesk
from superdesk.celery_app import celery
from superdesk.io.ingest import IngestResource, IngestService
from superdesk.io.registry import registered_feed_parsers, allowed_feed_parsers  # noqa
from superdesk.io.registry import registered_feeding_services, allowed_feeding_services  # noqa
from superdesk.io.registry import feeding_service_errors, publish_errors  # noqa
from superdesk.io.registry import FeedParserAllowedResource, FeedParserAllowedService
from superdesk.io.registry import FeedingServiceAllowedResource, FeedingServiceAllowedService

from superdesk.io.commands.add_provider import AddProvider  # noqa
from superdesk.io import importers  # noqa
from superdesk.io.commands.update_ingest import UpdateIngest, update_provider  # noqa
from superdesk.io.commands.remove_expired_content import RemoveExpiredContent
from superdesk.io.ingest_provider_model import IngestProviderResource, IngestProviderService


logger = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = 'ingest_providers'
    service = IngestProviderService(endpoint_name, backend=superdesk.get_backend())
    IngestProviderResource(endpoint_name, app=app, service=service)

    from .io_errors import IOErrorsService, IOErrorsResource
    endpoint_name = 'io_errors'
    service = IOErrorsService(endpoint_name, backend=superdesk.get_backend())
    IOErrorsResource(endpoint_name, app=app, service=service)

    endpoint_name = 'ingest'
    service = IngestService(endpoint_name, backend=superdesk.get_backend())
    IngestResource(endpoint_name, app=app, service=service)

    superdesk.register_resource(
        name='feed_parsers_allowed',
        resource=FeedParserAllowedResource,
        service=FeedParserAllowedService
    )
    superdesk.privilege(
        name='feed_parsers',
        label='Ingest Feed Parsers',
        description='User can maintain Ingest Feed Parsers.'
    )

    superdesk.register_resource(
        name='feeding_services_allowed',
        resource=FeedingServiceAllowedResource,
        service=FeedingServiceAllowedService
    )

    superdesk.privilege(
        name='feeding_services',
        label='Ingest Feed Services',
        description='User can maintain Ingest Feed Services.'
    )


superdesk.privilege(name='ingest_providers', label='Ingest Channels', description='User can maintain Ingest Channels.')


@celery.task(soft_time_limit=15)
def update_ingest():
    """Check ingest providers and trigger an update when appropriate."""
    UpdateIngest().run()


@celery.task(soft_time_limit=600)
def gc_ingest():
    RemoveExpiredContent().run()
