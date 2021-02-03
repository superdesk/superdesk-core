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
import warnings
from abc import ABCMeta, abstractmethod
from datetime import timedelta, datetime
from pytz import utc
from flask import current_app as app
import superdesk
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, SuperdeskIngestError
from superdesk.io.registry import registered_feed_parsers, restricted_feeding_service_parsers
from superdesk.utc import utcnow
from superdesk.utils import Timer

logger = logging.getLogger(__name__)

OLD_CONTENT_MINUTES = "INGEST_OLD_CONTENT_MINUTES"


class FeedingService(metaclass=ABCMeta):
    """
    Base Class for all Feeding Service classes.

    A Feeding Service class must have the following attributes:
        1. `NAME` - unique name under which to register the class.
        2. `ERRORS` - representing a list of <error_number, error_message> pairs that might be raised by the class
                      instances' methods.

    Optional attributes:
        1. label: service label for UI view
        2. fields: list of dictionaries; contains the descriptions of configuration fields. All fields must
            have the following properties:
                - id: field identifier
                - type: valid values: text, password, boolean, mapping, choices, url_request
            Optional properties:
                - label: field label for UI view
                - required: if true the field is required
                - errors: dictionary of with key being the error code and value the error description
                - required_expression: if the evaluation of the expression is true the field is required
                    on validation. Field values can be referred by enclosing the field identifier in
                    accolades: {field_id}
                - readonly: if true, the field is not editable
                - show_expression: if the evaluation of the expression is true the field is displayed.
                    Field values can be referred by enclosing the field identifier in accolades: {field_id}
                - default_value: value to use
            Type specific properties:
                properties with a ``*`` are mandatory
                - url_request *: a dict containing the following keys:
                    - url *: URL to request
            The fields can be of the following types:
                1. text: has the following properties besides the generic ones:
                    - placeholder: placeholder text
                2. password
                3. boolean
                4. mapping: defines a mapping from a list of controlled values to values inputed by the user
                    and has the following properties besides the generic ones:
                    - add_mapping_label: label for add mapping button
                    - remove_mapping_label: label for mapping removal button
                    - empty_label: label to display when the mapping is empty
                    - first_field_options: dictionary with the following keys:
                        - label
                        - values: list of available options
                    - second_field_options: dictionary with the following keys:
                        - label
                        - placeholder
                5. choices: render field as a dropdown. Has the following properties besides the generic ones:
                    - choices: a tuple of tuples which defines keys and values for dropdown. Example:
                        'choices': (
                            ('key_one', 'Key one'),
                            ('key_two', 'Key two'),
                        )
                    - default: preselect value in dropdown. Must be value from 'choices' preperties.
    """

    def __init__(self):
        self._timer = Timer()
        self._provider = None

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

    def _test_feed_parser(self, provider):
        """
        Checks if the feed_parser value was in the restricted values list.

        :param provider: ingest provider document
        """
        feeding_service = provider.get("feeding_service")
        feed_parser = provider.get("feed_parser")

        if (
            feeding_service
            and feed_parser
            and restricted_feeding_service_parsers.get(feeding_service)
            and not restricted_feeding_service_parsers.get(feeding_service).get(feed_parser)
        ):
            raise SuperdeskIngestError.invalidFeedParserValue(provider=provider)

    def _test(self, provider):
        """
        Subclasses should override this method and do specific config test.

        :param provider: ingest provider document
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
        self._test_feed_parser(provider)
        return self._test(provider)

    def _is_closed(self, provider):
        """Test if provider is closed.

        :param provider: provider data
        :return bool: True if is closed
        """
        is_closed = provider.get("is_closed", False)

        if isinstance(is_closed, datetime):
            is_closed = False

        return is_closed

    def _log_msg(self, msg, level="info"):
        getattr(logger, level)("Ingest:{} '{}': {}".format(self._provider["_id"], self._provider["name"], msg))

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
            raise SuperdeskApiError.internalError("Ingest Provider is closed")
        else:
            try:
                self._provider = provider
                self._log_msg("Start update execution.")
                self._timer.start("update")

                return self._update(provider, update) or []
            except SuperdeskIngestError as error:
                self.close_provider(provider, error)
                raise error
            finally:
                self._log_msg("Stop update execution. Exec time: {:.4f} secs.".format(self._timer.stop("update")))
                # just in case stop all timers
                self._timer.stop_all()

    def close_provider(self, provider, error, force=False):
        """Closes the provider and uses error as reason for closing.

        :param provider: Ingest Provider Details.
                .. seealso:: :class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :param error: ingest error
        :param force: force closing of provider, no matter how it's configured
        """
        if provider.get("critical_errors", {}).get(str(error.code)) or force:
            updates = {
                "is_closed": True,
                "last_closed": {
                    "closed_at": utcnow(),
                    "message": "Channel closed due to critical error: {}".format(error),
                },
            }

            get_resource_service("ingest_providers").system_update(
                provider[superdesk.config.ID_FIELD], updates, provider
            )

    def add_timestamps(self, item):
        warnings.warn("deprecated, use localize_timestamps", DeprecationWarning)
        self.localize_timestamps(item)

    def localize_timestamps(self, item):
        """Make sure timestamps are in UTC."""
        for timestamp in ("firstcreated", "versioncreated"):
            if item.get(timestamp):
                item[timestamp] = utc.localize(item[timestamp])

    def is_latest_content(self, last_updated, provider_last_updated=None):
        """
        Parse file only if it's not older than provider last update -10m
        """

        if not provider_last_updated:
            provider_last_updated = utcnow() - timedelta(days=7)

        return provider_last_updated - timedelta(minutes=app.config[OLD_CONTENT_MINUTES]) < last_updated

    def is_old_content(self, last_updated):
        """Test if file is old so it wouldn't probably work in is_latest_content next time.

        Such files can be moved to `_ERROR` folder, it wouldn't be ingested anymore.

        :param last_updated: file last updated datetime
        """
        return last_updated < utcnow() - timedelta(minutes=app.config[OLD_CONTENT_MINUTES])

    def log_item_error(self, err, item, provider):
        """TODO: put item into provider error basket."""
        logger.warning(
            "ingest error msg={} item={} provider={}".format(str(err), item.get("guid"), provider.get("name"))
        )

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

        parser = registered_feed_parsers.get(provider.get("feed_parser", ""))
        if not parser:
            raise SuperdeskIngestError.parserNotFoundError(provider=provider)

        if article is not None and not parser.can_parse(article):
            raise SuperdeskIngestError.parserNotFoundError(provider=provider)

        if article is not None:
            parser = parser.__class__()

        return parser


# must be imported for registration
from superdesk.io.feeding_services.email import EmailFeedingService  # NOQA
from superdesk.io.feeding_services.gmail import GMailFeedingService  # NOQA
from superdesk.io.feeding_services.file_service import FileFeedingService  # NOQA
from superdesk.io.feeding_services.ftp import FTPFeedingService  # NOQA
from superdesk.io.feeding_services.ritzau import RitzauFeedingService  # NOQA
from superdesk.io.feeding_services.http_service import HTTPFeedingService  # NOQA
from superdesk.io.feeding_services.rss import RSSFeedingService  # NOQA
from superdesk.io.feeding_services.twitter import TwitterFeedingService  # NOQA
from superdesk.io.feeding_services.ap import APFeedingService  # NOQA
from superdesk.io.feeding_services.bbc_ldrs import BBCLDRSFeedingService  # NOQA
from superdesk.io.feeding_services.ap_media import APMediaFeedingService  # NOQA


def init_app(app):
    # app needs to be accessible for those feeding services
    GMailFeedingService.init_app(app)
