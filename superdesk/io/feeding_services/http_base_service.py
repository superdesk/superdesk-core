# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import List, Dict
import traceback
import requests
from superdesk.errors import IngestApiError, SuperdeskIngestError
from superdesk.io.feeding_services import FeedingService


class HTTPFeedingServiceBase(FeedingService):
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
    HTTP_URL = None
    # timeout in seconds
    HTTP_TIMEOUT = 30
    # if some parameters are used in every request, put them here
    HTTP_DEFAULT_PARAMETERS = None
    # Set to True if authentication is mandatory, False if there is no authentication
    # and None to add authentication if user and password are defined.
    # If auth_required is defined in config fields, it will override this value.
    HTTP_AUTH = True

    # use this when auth is always required
    AUTH_FIELDS: List[Dict] = [
        {"id": "username", "type": "text", "label": "Username", "placeholder": "Username", "required": True},
        {"id": "password", "type": "password", "label": "Password", "placeholder": "Password", "required": True},
    ]

    # use this when auth depends of a "auth_required" flag (set by user)
    AUTH_REQ_FIELDS: List[Dict] = [
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
            "required_expression": "{auth_required}",
            "show_expression": "{auth_required}",
        },
        {
            "id": "password",
            "type": "password",
            "label": "Password",
            "placeholder": "Password",
            "required_expression": "{auth_required}",
            "show_expression": "{auth_required}",
        },
    ]

    def __init__(self):
        super().__init__()
        self.token = None

    @property
    def auth_info(self):
        """Helper method to retrieve a dict with username and password when set"""
        username = self.config.get("username", "")
        password = self.config.get("password", "")
        if not username or not password:
            return None
        return {"username": username, "password": password}

    @property
    def config(self):
        return self.provider.setdefault("config", {})

    def validate_config(self):
        """
        Validate provider config according to `cls.fields`

        :param config: Ingest provider configuration
        :type config: dict
        :return:
        """
        # validate required config fields
        required_keys = [field["id"] for field in self.fields if field.get("required", False)]
        if not set(self.config.keys()).issuperset(required_keys):
            raise SuperdeskIngestError.notConfiguredError(
                Exception("{} are required.".format(", ".join(required_keys)))
            )

        # validate url
        url = self.config.get("url")
        if url and not url.strip().startswith("http"):
            raise SuperdeskIngestError.notConfiguredError(Exception("URL must be a valid HTTP link."))

    def get_url(self, url=None, **kwargs):
        """Do an HTTP Get on URL

        :param string url: url to use (None to use self.HTTP_URL)
        :param **kwargs: extra parameter for requests
        :return requests.Response: response
        """
        if not url:
            url = self.HTTP_URL
        config = self.config
        user = config.get("username")
        password = config.get("password")
        if user:
            user = user.strip()
        if password:
            password = password.strip()

        auth_required = config.get("auth_required", self.HTTP_AUTH)
        if auth_required is None:
            # auth_required may not be user in the feeding service
            # in this case with use authentification only if user
            # and password are set.
            auth_required = bool(user and password)

        if auth_required:
            if not user:
                raise SuperdeskIngestError.notConfiguredError("user is not configured")
            if not password:
                raise SuperdeskIngestError.notConfiguredError("password is not configured")
            kwargs.setdefault("auth", (user, password))

        params = kwargs.pop("params", {})
        if params or self.HTTP_DEFAULT_PARAMETERS:
            # if we have default parameters, we want them to be overriden
            # by conflicting params given in arguments
            if self.HTTP_DEFAULT_PARAMETERS:
                params.update(self.HTTP_DEFAULT_PARAMETERS)
            kwargs["params"] = params

        try:
            response = requests.get(url, timeout=self.HTTP_TIMEOUT, **kwargs)
        except requests.exceptions.Timeout as exception:
            raise IngestApiError.apiTimeoutError(exception, self.provider)
        except requests.exceptions.ConnectionError as exception:
            raise IngestApiError.apiConnectionError(exception, self.provider)
        except requests.exceptions.RequestException as exception:
            raise IngestApiError.apiRequestError(exception, self.provider)
        except Exception as exception:
            traceback.print_exc()
            raise IngestApiError.apiGeneralError(exception, self.provider)

        if not response.ok:
            exc = Exception(response.reason)
            if response.status_code in (401, 403):
                raise IngestApiError.apiAuthError(exc, self.provider)
            elif response.status_code == 404:
                raise IngestApiError.apiNotFoundError(exc, self.provider)
            else:
                raise IngestApiError.apiGeneralError(exc, self.provider)

        return response

    def update(self, provider, update):
        self.provider = provider
        self.validate_config()
        return super().update(provider, update)
