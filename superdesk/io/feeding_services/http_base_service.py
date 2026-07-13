# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from io import BytesIO
import traceback
import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import aiohttp

from superdesk.errors import IngestApiError, SuperdeskIngestError
from superdesk.etree import etree, ParseError
from superdesk.core import json
from superdesk.core.web import AsyncHttpClientSessionMixin
from superdesk.io.feeding_services import FeedingService
from superdesk.media.media_operations import download_file_from_url_async


logger = logging.getLogger(__name__)


class HTTPFeedingServiceBase(FeedingService, AsyncHttpClientSessionMixin):
    """
    Base class for feeding services using HTTP.

    This class contains helpers to make the creation of HTTP based feeding services
    easier.

    There are a couple of class attributes you can use:

    =======================  ===========
    Attribute                Explanation
    =======================  ===========
    HTTP_URL                 Main URL of your service, will be used by default in get_url
    HTTP_TIMEOUT             Timeout of requests in seconds
    HTTP_DEFAULT_PARAMETERS  Parameters used in every ``get`` requests.
                             Will be updated with params set in arguments
    HTTP_AUTH                Indicate if HTTP authentication is needed for your service.
                             If None, the authentication will be determined by the existence
                             of user and password. Will be overriden by auth_required config
                             if it exists.
    =======================  ===========

    In addition, you have some pre-filled fields:

    ===============  ===========
    Field            Explanation
    ===============  ===========
    AUTH_FIELDS      username and password fields
    AUTH_REQ_FIELDS  username and password fields + auth_required field to indicate
                     if they are needed
    ===============  ===========

    When ingest is updated, the provider is automatically saved to ``self.provider``.
    ``config`` property allows to access easily the user configuration.
    ``auth_info`` property returns a dictionary with ``username`` and ``password``

    ``get_url`` method do a HTTP Get request. url can be ommited in which case HTTP_URL will be used.
    Authentication parameters are set automatically, and errors are catched appropriately.
    Extra arguments are used directly in *requests* call.

    """

    ERRORS = [
        IngestApiError.apiTimeoutError().get_error_description(),
        IngestApiError.apiRequestError().get_error_description(),
        IngestApiError.apiGeneralError().get_error_description(),
        SuperdeskIngestError.notConfiguredError().get_error_description(),
    ]

    # override this parameter with the main URL to use
    HTTP_URL: str | None = None
    # timeout in seconds
    HTTP_TIMEOUT = 30
    # if some parameters are used in every request, put them here
    HTTP_DEFAULT_PARAMETERS = None
    # Set to True if authentication is mandatory, False if there is no authentication
    # and None to add authentication if user and password are defined.
    # If auth_required is defined in config fields, it will override this value.
    HTTP_AUTH: bool | None = True

    # use this when auth is always required
    AUTH_FIELDS: list[dict] = [
        {"id": "username", "type": "text", "label": "Username", "placeholder": "Username", "required": True},
        {"id": "password", "type": "password", "label": "Password", "placeholder": "Password", "required": True},
    ]

    # use this when auth depends of a "auth_required" flag (set by user)
    AUTH_REQ_FIELDS: list[dict] = [
        {
            "id": "auth_required",
            "type": "boolean",
            "label": "Requires Authentication",
            "placeholder": "Requires Authentication",
            "required": False,
        },
        {
            "id": "username",
            "type": "text",
            "label": "Username",
            "placeholder": "Username",
            "required_expression": "provider.config.auth_required === true",
            "show_expression": "provider.config.auth_required === true",
        },
        {
            "id": "password",
            "type": "password",
            "label": "Password",
            "placeholder": "Password",
            "required_expression": "provider.config.auth_required === true",
            "show_expression": "provider.config.auth_required === true",
        },
    ]

    def __init__(self):
        super().__init__()
        self.token = None

    @property
    def auth_info(self) -> tuple[str | None, str | None]:
        """Helper method to retrieve a dict with username and password when set"""
        username: str | None = self.config.get("username", "")
        password: str | None = self.config.get("password", "")

        return username.strip() if username else None, password.strip() if password else None

    @property
    def config(self):
        return self.provider.setdefault("config", {})

    async def validate_config(self):
        """
        Validate provider config according to `cls.fields`

        :param config: Ingest provider configuration
        :type config: dict
        :return:
        """
        # validate required config fields
        required_keys = [field["id"] for field in self.fields if field.get("required", False)]
        if not set(self.config.keys()).issuperset(required_keys):
            raise await SuperdeskIngestError.notConfiguredError(
                Exception("{} are required.".format(", ".join(required_keys)))
            ).send_notifications()

        # validate url
        url = self.config.get("url")
        if url and not url.strip().startswith("http"):
            raise await SuperdeskIngestError.notConfiguredError(
                Exception("URL must be a valid HTTP link.")
            ).send_notifications()

    def get_request_kwargs(self) -> dict:
        return {}

    @classmethod
    def _create_http_session(cls) -> aiohttp.ClientSession:
        if isinstance(cls.HTTP_TIMEOUT, tuple):
            cls.http_timeout = aiohttp.ClientTimeout(connect=cls.HTTP_TIMEOUT[0], sock_read=cls.HTTP_TIMEOUT[1])
        elif isinstance(cls.HTTP_TIMEOUT, int):
            cls.http_timeout = aiohttp.ClientTimeout(total=cls.HTTP_TIMEOUT)

        return super()._create_http_session()

    async def get_auth_header(self) -> aiohttp.BasicAuth | None:
        username, password = self.auth_info
        auth_required = self.config.get("auth_required", self.HTTP_AUTH)

        if auth_required is None:
            # auth_required may not be user in the feeding service
            # in this case with use authentification only if user
            # and password are set.
            auth_required = bool(username and password)

        if auth_required:
            if not username:
                raise await SuperdeskIngestError.notConfiguredError("user is not configured").send_notifications()
            if not password:
                raise await SuperdeskIngestError.notConfiguredError("password is not configured").send_notifications()

            return aiohttp.BasicAuth(username, password)

        return None

    @asynccontextmanager
    async def get(self, url: str | None = None, **kwargs) -> AsyncIterator[aiohttp.ClientResponse]:
        """Do an HTTP Get on URL and yield the response"""

        if not url:
            url = self.HTTP_URL

        if not url:
            raise await SuperdeskIngestError.notConfiguredError("url is not configured").send_notifications()

        auth_header = await self.get_auth_header()
        params = kwargs.pop("params", {})
        if params or self.HTTP_DEFAULT_PARAMETERS:
            # if we have default parameters, we want them to be overriden
            # by conflicting params given in arguments
            if self.HTTP_DEFAULT_PARAMETERS:
                params.update(self.HTTP_DEFAULT_PARAMETERS)
            kwargs["params"] = params

        # Let the provided ``kwargs`` override the feeding service's ``kwargs``
        request_kwargs = self.get_request_kwargs()
        request_kwargs.update(kwargs)
        if auth_header:
            request_kwargs["auth"] = auth_header

        try:
            http_client = await self.http_session()
            async with http_client.get(url, **request_kwargs) as response:
                yield response
        except (asyncio.TimeoutError, TimeoutError) as exception:
            raise await IngestApiError.apiTimeoutError(exception, self.provider).send_notifications()
        except aiohttp.ClientConnectionError as exception:
            raise await IngestApiError.apiConnectionError(exception, self.provider).send_notifications()
        except aiohttp.ClientError as exception:
            raise await IngestApiError.apiRequestError(exception, self.provider).send_notifications()
        except asyncio.CancelledError:
            logger.exception("HTTPPush Asyncio Task Cancelled")
            raise
        except IngestApiError as exception:
            # Don't trap these errors, just re-raise them.
            raise await exception.send_notifications()
        except Exception as exception:
            traceback.print_exc()
            raise await IngestApiError.apiGeneralError(exception, self.provider).send_notifications()

    @asynccontextmanager
    async def get_url(self, url: str | None = None, **kwargs) -> AsyncIterator[aiohttp.ClientResponse]:
        """Do an HTTP Get on URL

        :param string url: url to use (None to use self.HTTP_URL)
        :param **kwargs: extra parameter for requests
        :return requests.Response: response
        """

        async with self.get(url, **kwargs) as response:
            if not response.ok:
                exc = Exception(response.reason)
                if response.status in (401, 403):
                    raise IngestApiError.apiAuthError(exc, self.provider)
                elif response.status == 404:
                    raise IngestApiError.apiNotFoundError(exc, self.provider)
                else:
                    raise IngestApiError.apiGeneralError(exc, self.provider)

            yield response

    async def get_json(self, url: str | None = None, **kwargs) -> dict:
        async with self.get_url(url, **kwargs) as response:
            response.raise_for_status()
            try:
                return json.loads(await response.text())
            except Exception:
                raise IngestApiError.apiRequestError(Exception("error parsing json response"))

    async def get_xml(self, url: str | None = None, **kwargs) -> etree._Element:
        async with self.get_url(url, **kwargs) as response:
            response.raise_for_status()
            try:
                return etree.fromstring(await response.read())
            except UnicodeEncodeError as error:
                raise IngestApiError.apiUnicodeError(error, self.provider)
            except ParseError as error:
                raise IngestApiError.apiParseError(error, self.provider)
            except Exception as error:
                raise IngestApiError.apiRequestError(error, self.provider)

    async def download_file_async(self, url: str, **kwargs) -> tuple[BytesIO, str, str]:
        request_kwargs = self.get_request_kwargs()
        request_kwargs.update(kwargs)
        return await download_file_from_url_async(url, request_kwargs, session=await self.http_session())

    async def update(self, provider, update):
        self.provider = provider
        await self.validate_config()
        return await super().update(provider, update)
