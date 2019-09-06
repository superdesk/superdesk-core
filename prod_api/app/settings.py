# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
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
    ELASTICSEARCH_INDEX,
    ELASTICSEARCH_URL,
    AMAZON_ACCESS_KEY_ID,
    AMAZON_SECRET_ACCESS_KEY,
    AMAZON_REGION,
    AMAZON_CONTAINER_NAME,
    AMAZON_S3_SUBFOLDER,
    AMAZON_OBJECT_ACL
)

SECRET_KEY = env('PRODAPI_SECRET_KEY', '')

PRODAPI_INSTALLED_APPS = (
    'prod_api.items',
)

PRODAPI_DOMAIN = {}

# NOTE: no trailing slash for the PRODAPI_URL setting!
PRODAPI_URL = env('PRODAPI_URL', 'http://localhost:5500')
MEDIA_PREFIX = env('MEDIA_PREFIX', '%s/assets' % PRODAPI_URL.rstrip('/'))
URL_PREFIX = env('PRODAPI_URL_PREFIX', 'api')
API_VERSION = 'v1'

# date formats
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'
ELASTIC_DATE_FORMAT = '%Y-%m-%d'
