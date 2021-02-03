# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
A module containing configuration of the Superdesk's production API.

The meaning of configuration options is described in the Eve framework
`documentation <http://python-eve.org/config.html#global-configuration>`_.
"""

from superdesk.default_settings import env, urlparse

from superdesk.default_settings import (  # noqa
    DEBUG,
    SUPERDESK_TESTING,
    MONGO_URI,
    ELASTICSEARCH_INDEX,
    ELASTICSEARCH_URL,
    AMAZON_ACCESS_KEY_ID,
    AMAZON_SECRET_ACCESS_KEY,
    AMAZON_REGION,
    AMAZON_CONTAINER_NAME,
    AMAZON_S3_SUBFOLDER,
    AMAZON_OBJECT_ACL,
    AMAZON_ENDPOINT_URL,
    strtobool,
)

SECRET_KEY = env("PRODAPI_SECRET_KEY", "")

PRODAPI_INSTALLED_APPS = (
    "prod_api.items",
    "prod_api.assets",
    "prod_api.desks",
    "prod_api.planning",
    "prod_api.contacts",
    "prod_api.users",
)

# NOTE: no trailing slash for the PRODAPI_URL setting!
PRODAPI_URL = env("PRODAPI_URL", "http://localhost:5500")
URL_PREFIX = env("PRODAPI_URL_PREFIX", "prodapi")
API_VERSION = "v1"
MEDIA_PREFIX = env("MEDIA_PREFIX", "{}/{}/{}/assets".format(PRODAPI_URL.rstrip("/"), URL_PREFIX, API_VERSION))

# date formats
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S+0000"
ELASTIC_DATE_FORMAT = "%Y-%m-%d"

# response in json
XML = False

# authorisation server
AUTH_SERVER_SHARED_SECRET = env("AUTH_SERVER_SHARED_SECRET", "")

# authentication
PRODAPI_AUTH_ENABLED = strtobool(env("PRODAPI_AUTH_ENABLED", "true"))
