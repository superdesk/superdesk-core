# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import datetime
import traceback
import superdesk
import requests
from flask import current_app as app

from superdesk.errors import IngestApiError
from superdesk.etree import etree, ParseError
from superdesk.io import register_feeding_service
from superdesk.io.feeding_services.http_service import HTTPFeedingService
from superdesk.logging import logger
from superdesk.utc import utcnow
from urllib.parse import urlparse, urlunparse


requests.packages.urllib3.disable_warnings()


class ReutersHTTPFeedingService(HTTPFeedingService):
    """
    Feeding Service class which can read article(s) using HTTP provided by Reuters.
    """

    NAME = 'reuters_http'

    ERRORS = [IngestApiError.apiTimeoutError().get_error_description(),
              IngestApiError.apiRedirectError().get_error_description(),
              IngestApiError.apiRequestError().get_error_description(),
              IngestApiError.apiUnicodeError().get_error_description(),
              IngestApiError.apiParseError().get_error_description(),
              IngestApiError.apiGeneralError().get_error_description()]

    DATE_FORMAT = '%Y.%m.%d.%H.%M'

    def _update(self, provider, update):
        updated = utcnow()

        last_updated = provider.get('last_updated')
        ttl_minutes = app.config['INGEST_EXPIRY_MINUTES']
        if not last_updated or last_updated < updated - datetime.timedelta(minutes=ttl_minutes):
            last_updated = updated - datetime.timedelta(minutes=ttl_minutes)

        self.provider = provider
        provider_config = provider.get('config')
        if not provider_config:
            provider_config = {}
            provider['config'] = provider_config

        provider_config.setdefault('url', 'http://rmb.reuters.com/rmd/rest/xml')
        provider_config.setdefault('auth_url', 'https://commerce.reuters.com/rmd/rest/xml/login')
        self.URL = provider_config.get('url')

        for channel in self._get_channels():
            ids = self._get_article_ids(channel, last_updated, updated)
            for id in ids:
                try:
                    items = self.fetch_ingest(id)
                    if items:
                        yield items
                # if there was an exception processing the one of the bunch log it and continue
                except Exception as ex:
                    logger.warn('Reuters item {} has not been retrieved'.format(id))
                    logger.exception(ex)

    def _get_channels(self):
        """Get subscribed channels."""
        channels = []
        tree = self._get_tree('channels')
        for channel in tree.findall('channelInformation'):
            channels.append(channel.find('alias').text)

        return channels

    def _get_tree(self, endpoint, payload=None):
        """Get xml response for given API endpoint and payload.

        :param: endpoint
        :type endpoint: str
        :param: payload
        :type payload: str
        """

        if payload is None:
            payload = {}

        payload['token'] = self._get_auth_token(self.provider, update=True)
        url = self._get_absolute_url(endpoint)

        try:
            response = requests.get(url, params=payload, timeout=15)
        except requests.exceptions.Timeout as ex:
            # Maybe set up for a retry, or continue in a retry loop
            raise IngestApiError.apiTimeoutError(ex, self.provider)
        except requests.exceptions.TooManyRedirects as ex:
            # Tell the user their URL was bad and try a different one
            raise IngestApiError.apiRedirectError(ex, self.provider)
        except requests.exceptions.RequestException as ex:
            # catastrophic error. bail.
            raise IngestApiError.apiRequestError(ex, self.provider)
        except Exception as error:
            traceback.print_exc()
            raise IngestApiError.apiGeneralError(error, self.provider)

        if response.status_code == 404:
            raise LookupError('Not found %s' % payload)

        try:
            return etree.fromstring(response.content)  # workaround for http mock lib
        except UnicodeEncodeError as error:
            traceback.print_exc()
            raise IngestApiError.apiUnicodeError(error, self.provider)
        except ParseError as error:
            traceback.print_exc()
            raise IngestApiError.apiParseError(error, self.provider)
        except Exception as error:
            traceback.print_exc()
            raise IngestApiError.apiGeneralError(error, self.provider)

    def _get_absolute_url(self, endpoint):
        """
        Get absolute URL for given endpoint.

        :param: endpoint
        :type endpoint: str
        """
        return '/'.join([self.URL, endpoint])

    def _get_article_ids(self, channel, last_updated, updated):
        """
        Get article ids which should be upserted also save the poll token that is returned.
        """
        ids = set()
        payload = {'channel': channel, 'fieldsRef': 'id'}

        # check if the channel has a pollToken if not fall back to dateRange
        last_poll_token = self._get_poll_token(channel)
        if last_poll_token is not None:
            logger.info("Reuters requesting channel {} with poll token {}".format(channel, last_poll_token))
            payload['pollToken'] = last_poll_token
        else:
            payload['dateRange'] = "%s-%s" % (self._format_date(last_updated), self._format_date(updated))
            logger.info("Reuters requesting channel {} with dateRange {}".format(channel, payload['dateRange']))

        tree = self._get_tree('items', payload)
        status_code = tree.find('status').get('code') if tree.tag == 'results' else tree.get('code')
        # check the returned status
        if status_code != '10':
            logger.warn("Reuters channel request returned status code {}".format(status_code))
            # status code 30 indicates failure
            if status_code == '30':
                # invalid token
                logger.warn("Reuters error on channel {} code {} {}".format(channel, tree.find('error').get('code'),
                                                                            tree.find('error').text))
                if tree.find('error').get('code') == '2100':
                    self._save_poll_token(channel, None)
                    logger.warn("Reuters channel invalid token reseting {}".format(status_code))
                return ids

        # extract the returned poll token if there is one
        poll_token = tree.find('pollToken')
        if poll_token is not None:
            # a new token indicated new content
            if poll_token.text != last_poll_token:
                logger.info("Reuters channel {} new token {}".format(channel, poll_token.text))
                self._save_poll_token(channel, poll_token.text)
            else:
                # the token has not changed, so nothing new
                logger.info("Reuters channel {} nothing new".format(channel))
                return ids
        else:
            logger.info("Reuters channel {} retrieved no token".format(channel))
            return ids

        for result in tree.findall('result'):
            id = result.find('id').text
            ids.add(id)
            logger.info("Reuters id : {}".format(id))

        return ids

    def _save_poll_token(self, channel, poll_token):
        """Saves the poll token for the passed channel in the config section of the

        :param channel:
        :param poll_token:
        :return:
        """
        # get the provider in case it has been updated by another channel
        ingest_provider_service = superdesk.get_resource_service('ingest_providers')
        provider = ingest_provider_service.find_one(req=None, _id=self.provider[superdesk.config.ID_FIELD])
        provider_token = provider.get('tokens')
        if 'poll_tokens' not in provider_token:
            provider_token['poll_tokens'] = {channel: poll_token}
        else:
            provider_token['poll_tokens'][channel] = poll_token
        upd_provider = {'tokens': provider_token}
        ingest_provider_service.system_update(self.provider[superdesk.config.ID_FIELD], upd_provider, self.provider)

    def _get_poll_token(self, channel):
        """Get the poll token from provider config if it is available.

        :param channel:
        :return: token
        """
        if 'tokens' in self.provider and 'poll_tokens' in self.provider['tokens']:
            return self.provider.get('tokens').get('poll_tokens').get(channel, None)

    def _format_date(self, date):
        return date.strftime(self.DATE_FORMAT)

    def fetch_ingest(self, id):
        items = self._parse_items(id)
        result_items = []
        while items:
            item = items.pop()
            self.add_timestamps(item)
            try:
                items.extend(self._fetch_items_in_package(item))
                result_items.append(item)
            except LookupError as err:
                self.log_item_error(err, item, self.provider)
                return []

        return result_items

    def _parse_items(self, id):
        """
        Parse item message and return given items.
        """

        payload = {'id': id}
        tree = self._get_tree('item', payload)

        parser = self.get_feed_parser(self.provider, tree)
        items = parser.parse(tree, self.provider)

        return items

    def _fetch_items_in_package(self, item):
        """
        Fetch remote assets for given item.
        """
        items = []
        for group in item.get('groups', []):
            for ref in group.get('refs', []):
                if 'residRef' in ref:
                    items.extend(self._parse_items(ref.get('residRef')))

        return items

    def prepare_href(self, href, mimetype=None):
        (scheme, netloc, path, params, query, fragment) = urlparse(href)
        new_href = urlunparse((scheme, netloc, path, '', '', ''))
        return '%s?auth_token=%s' % (new_href, self._get_auth_token(self.provider, update=True))


register_feeding_service(ReutersHTTPFeedingService.NAME, ReutersHTTPFeedingService(), ReutersHTTPFeedingService.ERRORS)
