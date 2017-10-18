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
A module containing configuration of the Superdesk's public API.

The meaning of configuration options is described in the Eve framework
`documentation <http://python-eve.org/config.html#global-configuration>`_.
"""

from superdesk.default_settings import env, urlparse

from superdesk.default_settings import (  # noqa
    SECRET_KEY, MONGO_DBNAME, MONGO_URI,
    CONTENTAPI_MONGO_DBNAME, CONTENTAPI_MONGO_URI,
    CONTENTAPI_ELASTICSEARCH_URL, CONTENTAPI_ELASTICSEARCH_INDEX,
    AMAZON_ACCESS_KEY_ID, AMAZON_SECRET_ACCESS_KEY, AMAZON_REGION,
    AMAZON_CONTAINER_NAME, AMAZON_S3_SUBFOLDER, AMAZON_OBJECT_ACL,
)

CONTENTAPI_INSTALLED_APPS = [
    'content_api.items',
    'content_api.packages',
    'content_api.assets',
    'content_api.tokens',
    'content_api.items_versions',
    'content_api.packages_versions',
    'content_api.api_audit',
]

CONTENTAPI_DOMAIN = {}

# NOTE: no trailing slash for the CONTENTAPI_URL setting!
CONTENTAPI_URL = env('CONTENTAPI_URL', 'http://localhost:5400')
MEDIA_PREFIX = env('MEDIA_PREFIX', '%s/assets' % CONTENTAPI_URL.rstrip('/'))
server_url = urlparse(CONTENTAPI_URL)
URL_PREFIX = env('CONTENTAPI_URL_PREFIX', server_url.path.strip('/')) or ''
VERSION = '_current_version'

XML = False
PUBLIC_RESOURCES = []
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'
ELASTIC_DATE_FORMAT = '%Y-%m-%d'
BCRYPT_GENSALT_WORK_FACTOR = 12
