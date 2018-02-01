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
from abc import ABCMeta, abstractmethod
from datetime import datetime

from pytz import utc

import superdesk
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, SuperdeskIngestError
from superdesk.io.registry import registered_feed_parsers
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


class FeedingService(metaclass=ABCMeta):
    """
    Base Class for all Feeding Service classes.

    A Feeding Service class must have the following attributes:
        1. `NAME` - unique name under which to register the class.
        2. `ERRORS` - representing a list of <error_number, error_message> pairs that might be raised by the class
                      instances' methods.
    """

    @abstractmethod
    def _update(self, provider, update):
        """
        Subclasses must override this method and get items from the provider as per the configuration.

        :param provider: Ingest Provider Details.
                .. seealso:: :class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :type provider: dict
        :param update: Any update that is required on provider.
        :type update: dict
        :return: a list of articles which can be saved in Ingest Collection.
        """
        raise NotImplementedError()

    def _test(self, provider):
        """
        Subclasses should override this method and do specific config test.

        :param provider: Ingest Provider Details.
        """
        return

    def config_test(self, provider=None):
        """Test provider configuration.

        :param provider: provider data
        """
        if not provider:  # nosetests run this for some reason
            return
        if self._is_closed(provider):
            return
        return self._test(provider)

    def _is_closed(self, provider):
        """Test if provider is closed.

        :param provider: provider data
        :return bool: True if is closed
        """
        is_closed = provider.get('is_closed', False)

        if isinstance(is_closed, datetime):
            is_closed = False

        return is_closed

    def update(self, provider, update):
        """
        Clients consuming Ingest Services should invoke this to get items from the provider.

        :param provider: Ingest Provider Details.
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :param update: Any update that is required on provider.
        :type update: dict
        :return: a list of articles which can be saved in Ingest Collection.
        :raises SuperdeskApiError.internalError if Provider is closed
        :raises SuperdeskIngestError if failed to get items from provider
        """
        if self._is_closed(provider):
            raise SuperdeskApiError.internalError('Ingest Provider is closed')
        else:
            try:
                return self._update(provider, update) or []
            except SuperdeskIngestError as error:
                self.close_provider(provider, error)
                raise error

    def close_provider(self, provider, error, force=False):
        """Closes the provider and uses error as reason for closing.

        :param provider: Ingest Provider Details.
                .. seealso:: :class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :param error: ingest error
        :param force: force closing of provider, no matter how it's configured
        """
        if provider.get('critical_errors', {}).get(str(error.code)) or force:
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

    def prepare_href(self, href, mimetype=None):
        """Prepare a link to an external resource (e.g. an image file).

        It can be directly used by the ingest machinery for fetching it.

        Sub-classes can override this method if properties like HTTP Authentication need to be added to the href.

        :param href: the original URL as extracted from an RSS entry
        :type href: str
        :return: prepared URL
        :rtype: str
        """
        return href

    def get_feed_parser(self, provider, article=None):
        """
        Returns instance of configured feed parser for the given provider.

        :param provider: Ingest Provider Details.
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :param article: article which needs to parsed by the parser, defaults to None. When None, the registered parser
                        will be returned without checking if the parser can parse the article.
        :return: Feed Parser instance.
        :rtype: :py:class:`superdesk.io.feed_parsers.FeedParser`
        :raises: SuperdeskIngestError.parserNotFoundError()
                    if either feed_parser value is empty or Feed Parser not found.
        """

        parser = registered_feed_parsers.get(provider.get('feed_parser', ''))
        if not parser:
            raise SuperdeskIngestError.parserNotFoundError(provider=provider)

        if article is not None and not parser.can_parse(article):
            raise SuperdeskIngestError.parserNotFoundError(provider=provider)

        if article is not None:
            parser = parser.__class__()

        return parser


# must be imported for registration
from superdesk.io.feeding_services.email import EmailFeedingService  # NOQA
from superdesk.io.feeding_services.file_service import FileFeedingService  # NOQA
from superdesk.io.feeding_services.ftp import FTPFeedingService  # NOQA
from superdesk.io.feeding_services.ritzau import RitzauFeedingService  # NOQA
from superdesk.io.feeding_services.http_service import HTTPFeedingService  # NOQA
from superdesk.io.feeding_services.rss import RSSFeedingService  # NOQA
from superdesk.io.feeding_services.twitter import TwitterFeedingService  # NOQA
