# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import timedelta

import arrow

from superdesk.resource_fields import ID_FIELD
from superdesk import get_resource_service
from superdesk.errors import IngestApiError
from superdesk.utc import utcnow
from superdesk.etree import etree

from .http_base_service import HTTPFeedingServiceBase


class HTTPFeedingService(HTTPFeedingServiceBase):
    """
    Feeding Service class which can read article(s) using HTTP.
    """

    ERRORS = [
        IngestApiError.apiTimeoutError().get_error_description(),
        IngestApiError.apiRedirectError().get_error_description(),
        IngestApiError.apiRequestError().get_error_description(),
        IngestApiError.apiUnicodeError().get_error_description(),
        IngestApiError.apiParseError().get_error_description(),
        IngestApiError.apiGeneralError().get_error_description(),
    ]

    label = "HTTP"

    http_verify_ssl = False

    def __init__(self):
        super().__init__()
        self.token = None

    async def _generate_token_and_update_provider(self, provider):
        """
        Generates Authentication Token and updates the given provider with the authentication token.

        :param provider: dict - Ingest provider details to which the current directory has been configured
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: Authentication Token
        :rtype: str
        """
        token = {"auth_token": await self._generate_auth_token(provider), "created": utcnow()}
        await get_resource_service("ingest_providers").system_update_async(
            provider[ID_FIELD], updates={"tokens": token}, original=provider
        )
        provider["tokens"] = token
        return token["auth_token"]

    async def _generate_auth_token(self, provider):
        """
        Generates Authentication Token as per the configuration in Ingest Provider.

        :param provider: dict - Ingest provider details to which the current directory has been configured
        :type provider: dict :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: token details if successfully authenticated
        :rtype: str
        :raises: IngestApiError.apiGeneralError() if auth_url is missing in the Ingest Provider configuration
        """

        auth_url = provider.get("config", {}).get("auth_url", None)
        if not auth_url:
            raise await IngestApiError.apiGeneralError(
                provider=provider,
                exception=KeyError(
                    f"Ingest Provider {provider['name']} is missing Authentication URL. Please check the configuration."
                ),
            ).send_notifications()

        payload = {
            "username": provider.get("config", {}).get("username", ""),
            "password": provider.get("config", {}).get("password", ""),
        }

        http_client = await self.http_session()
        async with http_client.get(auth_url, params=payload) as response:
            if response.status < 200 or response.status >= 300:
                try:
                    response.raise_for_status()
                except Exception:
                    err = IngestApiError.apiAuthError(provider=provider)
                    await self.close_provider(provider, err, force=True)
                    await err.send_notifications()
                    raise err

            tree = etree.fromstring(await response.read())  # workaround for http mock lib
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
        created = arrow.get(token.get("created")).datetime

        return created + ttl >= utcnow() and token.get("auth_token")

    async def _get_auth_token(self, provider, update=False):
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
        token = provider.get("tokens")

        if token and self._is_valid_token(token):
            return token.get("auth_token")

        return await self._generate_token_and_update_provider(provider) if update else ""
