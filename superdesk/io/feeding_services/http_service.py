# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import ssl
from abc import ABCMeta
from datetime import timedelta

import arrow
import requests
from eve.utils import config
from requests.packages.urllib3.poolmanager import PoolManager

from superdesk import get_resource_service
from superdesk.errors import IngestApiError
from superdesk.io.feeding_services import FeedingService
from superdesk.utc import utcnow
from superdesk.etree import etree


class HTTPFeedingService(FeedingService, metaclass=ABCMeta):
    """
    Feeding Service class which can read article(s) using HTTP.
    """

    ERRORS = [IngestApiError.apiTimeoutError().get_error_description(),
              IngestApiError.apiRedirectError().get_error_description(),
              IngestApiError.apiRequestError().get_error_description(),
              IngestApiError.apiUnicodeError().get_error_description(),
              IngestApiError.apiParseError().get_error_description(),
              IngestApiError.apiGeneralError().get_error_description()]

    label = 'HTTP'

    def __init__(self):
        super().__init__()
        self.token = None

    def _generate_token_and_update_provider(self, provider):
        """
        Generates Authentication Token and updates the given provider with the authentication token.

        :param provider: dict - Ingest provider details to which the current directory has been configured
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: Authentication Token
        :rtype: str
        """
        token = {'auth_token': self._generate_auth_token(provider), 'created': utcnow()}
        get_resource_service('ingest_providers').system_update(provider[config.ID_FIELD], updates={'tokens': token},
                                                               original=provider)
        provider['tokens'] = token
        return token['auth_token']

    def _generate_auth_token(self, provider):
        """
        Generates Authentication Token as per the configuration in Ingest Provider.

        :param provider: dict - Ingest provider details to which the current directory has been configured
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: token details if successfully authenticated
        :rtype: str
        :raises: IngestApiError.apiGeneralError() if auth_url is missing in the Ingest Provider configuration
        """
        session = requests.Session()
        session.mount('https://', SSLAdapter())

        auth_url = provider.get('config', {}).get('auth_url', None)
        if not auth_url:
            raise IngestApiError.apiGeneralError(provider=provider,
                                                 exception=KeyError(
                                                     '''
                                                     Ingest Provider {} is missing Authentication URL.
                                                     Please check the configuration.
                                                     '''.format(provider['name']))
                                                 )

        payload = {
            'username': provider.get('config', {}).get('username', ''),
            'password': provider.get('config', {}).get('password', ''),
        }

        response = session.get(auth_url, params=payload, verify=False, timeout=30)
        if response.status_code < 200 or response.status_code >= 300:
            try:
                response.raise_for_status()
            except Exception:
                err = IngestApiError.apiAuthError(provider=provider)
                self.close_provider(provider, err, force=True)
                raise err

        tree = etree.fromstring(response.content)  # workaround for http mock lib
        return tree.text

    def _is_valid_token(self, token):
        """Check if the given token is still valid.

        Most of authentication tokens issued by Ingest Providers are valid for 12 hours.

        :param token: Token information
        :type token: dict
        :return: True if valid, False otherwise
        :rtype: bool
        """
        ttl = timedelta(hours=12)
        created = arrow.get(token.get('created')).datetime

        return created + ttl >= utcnow() and token.get('auth_token')

    def _get_auth_token(self, provider, update=False):
        """
        Gets authentication token for given provider instance and save it in db based on the given update flag.

        :param provider: dict - Ingest provider details to which the current directory has been configured
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :param update: a flag which dictates whether to save the authentication token in Ingest Provider record or not.
                       Saves if the value is True, defaults to False.
        :type update: bool
        :return: Authentication Token
        :rtype: str
        """
        token = provider.get('tokens')

        if token and self._is_valid_token(token):
            return token.get('auth_token')

        return self._generate_token_and_update_provider(provider) if update else ''


# workaround for ssl version error
class SSLAdapter(requests.adapters.HTTPAdapter):
    """
    SSL Adapter set for ssl tls v1.
    """

    def init_poolmanager(self, connections, maxsize, **kwargs):
        """
        Initializes pool manager to use ssl version v1.
        """

        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, ssl_version=ssl.PROTOCOL_TLSv1,
                                       **kwargs)
