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

import os
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


def env(variable, fallback_value=None):
    env_value = os.environ.get(variable, '')
    if len(env_value) == 0:
        return fallback_value
    else:
        if env_value == "__EMPTY__":
            return ''
        else:
            return env_value

CONTENTAPI_MONGO_DBNAME = 'contentapi'
CONTENTAPI_MONGO_URI = env('CONTENTAPI_MONGO_URI', 'mongodb://localhost/%s' % CONTENTAPI_MONGO_DBNAME)

ELASTICSEARCH_URL = env('CONTENTAPI_ELASTICSEARCH_URL', 'http://localhost:9200')
ELASTICSEARCH_INDEX = env('CONTENTAPI_ELASTICSEARCH_INDEX', CONTENTAPI_MONGO_DBNAME)
ELASTIC_DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'

OAUTH2_ROUTE_PREFIX = '/oauth'
OAUTH2_TOKEN_URL = '/token'
OAUTH2_SCOPES = ['content_api']
BCRYPT_GENSALT_WORK_FACTOR = 12
PUBLIC_RESOURCES = ['items', 'packages', 'publish', 'assets', 'clients', 'users']

CONTENTAPI_INSTALLED_APPS = [
    'content_api.items',
    'content_api.packages',
    'content_api.prepopulate',
    'content_api.publish',
    'content_api.assets',
    'content_api.clients',
    'content_api.users',
    'content_api.tokens',
    'content_api.auth'
]

DOMAIN = {}
CONTENTAPI_DOMAIN = {}

SUPERDESK_CONTENTAPI_TESTING = True

# NOTE: no trailing slash for the PUBLICAPI_URL setting!
PUBLICAPI_URL = env('PUBLICAPI_URL', 'http://localhost:5400')
server_url = urlparse(PUBLICAPI_URL)
URL_PREFIX = server_url.path.strip('/')
SERVER_NAME = server_url.netloc or None
URL_PROTOCOL = server_url.scheme or None

# Amazon S3 assets management
AMAZON_CONTAINER_NAME = env('AMAZON_CONTAINER_NAME', '')
AMAZON_ACCESS_KEY_ID = env('AMAZON_ACCESS_KEY_ID', '')
AMAZON_SECRET_ACCESS_KEY = env('AMAZON_SECRET_ACCESS_KEY', '')
AMAZON_REGION = env('AMAZON_REGION', 'us-east-1')
AMAZON_SERVE_DIRECT_LINKS = env('AMAZON_SERVE_DIRECT_LINKS', False)
AMAZON_S3_USE_HTTPS = env('AMAZON_S3_USE_HTTPS', False)
