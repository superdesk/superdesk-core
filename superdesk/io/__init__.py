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
from superdesk.errors import SuperdeskIngestError, AlreadyExistsError
from .commands.add_provider import AddProvider  # NOQA
from .ingest import IngestResource, IngestService

registered_feed_parsers = {}
allowed_feed_parsers = []

registered_feeding_services = {}
allowed_feeding_services = []
feeding_service_errors = {}
publish_errors = []

logger = logging.getLogger(__name__)


def init_app(app):
    from .ingest_provider_model import IngestProviderResource, IngestProviderService
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


superdesk.privilege(name='ingest_providers', label='Ingest Channels', description='User can maintain Ingest Channels.')


def register_feeding_service(service_name, service_class, errors):
    """
    Registers the Feeding Service with the application.
    :class: `superdesk.io.feeding_services.RegisterFeedingService` uses this function to register the feeding service.

    :param service_name: unique name to identify the Feeding Service class
    :param service_class: Feeding Service class
    :param errors: list of tuples, where each tuple represents an error that can be raised by a Feeding Service class.
                   Tuple syntax: (error_code, error_message)
    :raises: AlreadyExistsError if a feeding service with same name already been registered
    """

    if service_name in registered_feed_parsers:
        raise AlreadyExistsError('Feeding Service: {} already registered by {}'
                                 .format(service_name, type(registered_feeding_services[service_name])))

    registered_feeding_services[service_name] = service_class
    allowed_feeding_services.append(service_name)

    errors.append(SuperdeskIngestError.parserNotFoundError().get_error_description())
    feeding_service_errors[service_name] = dict(errors)


def register_feed_parser(parser_name, parser_class):
    """
    Registers the Feed Parser with the application.
    :class: `superdesk.io.feed_parsers.RegisterFeedParser` uses this function to register the feed parser.

    :param parser_name: unique name to identify the Feed Parser class
    :param parser_class: Feed Parser class
    :raises: AlreadyExistsError if a feed parser with same name already been registered
    """

    if parser_name in registered_feed_parsers:
        raise AlreadyExistsError('Feed Parser: {} already registered by {}'
                                 .format(parser_name, type(registered_feed_parsers[parser_name])))

    registered_feed_parsers[parser_name] = parser_class
    allowed_feed_parsers.append(parser_name)


@celery.task(soft_time_limit=15)
def update_ingest():
    from .commands.update_ingest import UpdateIngest
    UpdateIngest().run()


@celery.task
def gc_ingest():
    from .commands.remove_expired_content import RemoveExpiredContent
    RemoveExpiredContent().run()
