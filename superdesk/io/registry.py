# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk IO Registry"""

from superdesk import Resource, Service
from superdesk.utils import ListCursor
from superdesk.errors import SuperdeskIngestError, AlreadyExistsError

registered_feed_parsers = {}
allowed_feed_parsers = []

registered_feeding_services = {}
allowed_feeding_services = []
feeding_service_errors = {}
publish_errors = []
restricted_feeding_service_parsers = {}


def register_feeding_service(service_class):
    """
    Registers the Feeding Service with the application.

    :class: `superdesk.io.feeding_services.RegisterFeedingService` uses this function to register the feeding service.

    :param service_class: Feeding Service class
    :raises: AlreadyExistsError if a feeding service with same name already been registered
    """

    if service_class.NAME in registered_feeding_services:
        raise AlreadyExistsError(
            'Feeding Service: {} already registered by {}'.format(
                service_class.NAME,
                registered_feeding_services[service_class.NAME])
        )

    registered_feeding_services[service_class.NAME] = service_class
    allowed_feeding_services.append(service_class.NAME)

    service_class.ERRORS.append(SuperdeskIngestError.parserNotFoundError().get_error_description())
    feeding_service_errors[service_class.NAME] = dict(service_class.ERRORS)


def register_feeding_service_error(service_name, error):
    """
    Registers an error with the service named

    :param service_name: unique name to identify the Feeding Service class
    :param error: tuple representing the error, the tuple contains the error_code and the error message
    :return:
    """
    feeding_service_errors.get(service_name, {}).update(dict([error]))


def get_feeding_service(service_name):
    """
    Create and return Feeding Service instance.
    :param service_name: unique name to identify the Feeding Service class.
    :return: Feeding Service instance.
    :raise KeyError: there is no feeding service registered with this `service_name`.
    """

    return registered_feeding_services[service_name]()


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


def register_feeding_service_parser(service_name, parser_name):
    """
    Registers the Feed Parser with the Feeding service.

    :param service_name: unique name to identify the Feeding Service class
    :param parser_name: unique name to identify the Feed Parser class
        None if the feeding service doesn't expect any parser
    """
    if not restricted_feeding_service_parsers.get(service_name):
        restricted_feeding_service_parsers[service_name] = {}
    if parser_name is None:
        if restricted_feeding_service_parsers[service_name]:
            raise ValueError("You can't set None to a feeding service if some parsers are already registered")
        restricted_feeding_service_parsers[service_name] = None
    else:
        restricted_feeding_service_parsers[service_name][parser_name] = True


def get_feed_parser(parser_name):
    """
    Retrieve registered feed parser class from its name

    :param parser_name: name of the parser, as in register_feed_parser
    :type parser_name: str
    :return str: feed parser class
    :raise KeyError: there is no parser registered with this name
    """
    return registered_feed_parsers[parser_name]


class FeedParserAllowedResource(Resource):
    resource_methods = ['GET']
    item_methods = []
    allow_unknown = True


class FeedParserAllowedService(Service):

    def get(self, req, lookup):
        def parser(parser_id):
            registered = registered_feed_parsers[parser_id]
            return {
                'feed_parser': parser_id,
                'label': getattr(registered, 'label', parser_id)
            }

        return ListCursor(
            [parser(_id) for _id in registered_feed_parsers]
        )


class FeedingServiceAllowedResource(Resource):
    resource_methods = ['GET']
    item_methods = []
    schema = {
        'feeding_service': {'type': 'string'},
        'label': {'type': 'string'},
        'fields': {'type': 'list'},
        'field_groups': {'type': 'dict', 'schema': {}},
        'parser_restricted_values': {'type': 'list'},
    }


class FeedingServiceAllowedService(Service):

    def get(self, req, lookup):
        def service(service_id):
            feeding_service_class = registered_feeding_services[service_id]
            restricted_parsers = restricted_feeding_service_parsers.get(service_id, {})
            if restricted_parsers is not None:
                restricted_parsers = list(restricted_parsers.keys())

            return {
                'feeding_service': service_id,
                'label': getattr(feeding_service_class, 'label', service_id),
                'fields': getattr(feeding_service_class, 'fields', []),
                'field_groups': getattr(feeding_service_class, 'field_groups', {}),
                'parser_restricted_values': restricted_parsers
            }

        return ListCursor(
            [service(_id) for _id in registered_feeding_services]
        )
