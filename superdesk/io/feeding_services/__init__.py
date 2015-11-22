# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from datetime import datetime

from pytz import utc

import superdesk
from superdesk.errors import SuperdeskApiError, SuperdeskIngestError
from superdesk.io import registered_feeding_services, register_feeding_service, registered_feed_parsers
from superdesk.utc import utcnow
from superdesk import get_resource_service

logger = logging.getLogger(__name__)


class RegisterFeedingService(type):
    """
    Metaclass for registering the Feeding Service classes with the application.

    A Feeding Service class must have the following attributes:
        1. `NAME` - unique name under which to register the class. If missing then raises AttributeError.
                    If it's not unique then raises TypeError.

        2. `ERRORS` - representing a list of <error_number, error_message> pairs that might be raised by the class
                      instances' methods.
    """

    def __new__(metacls, name, bases, attrs):
        if name.endswith('FeedingService') and name != 'FeedingService' and name != 'FileFeedingService':
            service_name = attrs.get('NAME')

            if not service_name:
                raise AttributeError("Feeding Service Class {} must define the NAME attribute.".format(name))

            if 'ERRORS' not in attrs:
                raise AttributeError("Feeding Service Class {} must define the ERRORS list attribute.".format(name))

            if service_name in registered_feeding_services:
                raise TypeError("Feeding Service {} already exists ({})."
                                .format(service_name, registered_feeding_services[service_name]))

            new_cls = super().__new__(metacls, name, bases, attrs)
            register_feeding_service(service_name, new_cls, new_cls.ERRORS)
        else:
            new_cls = super().__new__(metacls, name, bases, attrs)

        return new_cls


class FeedingService(metaclass=RegisterFeedingService):
    """
    Base Class for all Feeding Service classes.

    .. seealso:: :class:`superdesk.io.feeding_services.RegisterFeedingService`
    """

    def _update(self, provider):
        """
        Subclasses must override this method and get items from the provider as per the configuration.

        :param provider: Ingest Provider Details.
                .. seealso:: :class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :type provider: dict
        :return: a list of articles which can be saved in Ingest Collection.
        """

        raise NotImplementedError()

    def update(self, provider):
        """
        Clients consuming Ingest Services should invoke this to get items from the provider.

        :param provider: Ingest Provider Details.
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: a list of articles which can be saved in Ingest Collection.
        :raises SuperdeskApiError.internalError if Provider is closed
        :raises SuperdeskIngestError if failed to get items from provider
        """

        is_closed = provider.get('is_closed', False)

        if isinstance(is_closed, datetime):
            is_closed = False

        if is_closed:
            raise SuperdeskApiError.internalError('Ingest Provider is closed')
        else:
            try:
                return self._update(provider) or []
            except SuperdeskIngestError as error:
                self.close_provider(provider, error)
                raise error

    def close_provider(self, provider, error):
        """
        Closes the provider and uses error as reason for closing.
        :param provider: Ingest Provider Details.
                .. seealso:: :class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :type provider: dict
        :param error:
        :type error: :py:class: `superdes.errors.SuperdeskIngestError`
        """

        if provider.get('critical_errors', {}).get(str(error.code)):
            updates = {
                'is_closed': True,
                'last_closed': {
                    'closed_at': utcnow(),
                    'message': 'Channel closed due to critical error: {}'.format(error)
                }
            }

            get_resource_service('ingest_providers').system_update(provider[superdesk.config.ID_FIELD],
                                                                   updates, provider)

    def add_timestamps(self, item):
        """
        Adds firstcreated and versioncreated timestamps to item

        :param item: object which can be saved to ingest collection
        :type item: dict
        """

        item['firstcreated'] = utc.localize(item['firstcreated']) if item.get('firstcreated') else utcnow()
        item['versioncreated'] = utc.localize(item['versioncreated']) if item.get('versioncreated') else utcnow()

    def log_item_error(self, err, item, provider):
        """TODO: put item into provider error basket."""
        logger.warning('ingest error msg={} item={} provider={}'.format(
            str(err),
            item.get('guid'),
            provider.get('name')
        ))

    def get_feed_parser(self, provider, article):
        """
        Returns instance of configured feed parser for the given provider.

        :param provider: Ingest Provider Details.
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :param article: article which needs to parsed by the parser
        :return: Feed Parser instance.
        :rtype: :py:class:`superdesk.io.feed_parsers.FeedParser`
        :raises: SuperdeskIngestError.parserNotFoundError()
                    if either feed_parser value is empty or Feed Parser not found.
        """

        parser = registered_feed_parsers.get(provider.get('feed_parser', ''))
        if not parser:
            raise SuperdeskIngestError.parserNotFoundError(provider=provider)

        if not parser.can_parse(article):
            raise SuperdeskIngestError.parserNotFoundError(provider=provider)

        return parser
