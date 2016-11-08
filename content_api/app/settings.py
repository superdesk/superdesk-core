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

from superdesk.default_settings import env, urlparse, SECRET_KEY  # noqa


CONTENTAPI_MONGO_DBNAME = 'contentapi'
CONTENTAPI_MONGO_URI = env('CONTENTAPI_MONGO_URI', 'mongodb://localhost/%s' % CONTENTAPI_MONGO_DBNAME)

CONTENTAPI_ELASTICSEARCH_URL = env('CONTENTAPI_ELASTICSEARCH_URL', 'http://localhost:9200')
CONTENTAPI_ELASTICSEARCH_INDEX = env('CONTENTAPI_ELASTICSEARCH_INDEX', CONTENTAPI_MONGO_DBNAME)

ELASTIC_DATE_FORMAT = '%Y-%m-%d'

OAUTH2_ROUTE_PREFIX = '/oauth'
OAUTH2_TOKEN_URL = '/token'
OAUTH2_SCOPES = ['content_api']
BCRYPT_GENSALT_WORK_FACTOR = 12

CONTENTAPI_INSTALLED_APPS = [
    'content_api.items',
    'content_api.packages',
]

CONTENTAPI_DOMAIN = {}

# NOTE: no trailing slash for the PUBLICAPI_URL setting!
PUBLICAPI_URL = env('PUBLICAPI_URL', 'http://localhost:5400')
server_url = urlparse(PUBLICAPI_URL)
URL_PREFIX = server_url.path.strip('/')

# Amazon S3 assets management
AMAZON_CONTAINER_NAME = env('AMAZON_CONTAINER_NAME', '')
AMAZON_ACCESS_KEY_ID = env('AMAZON_ACCESS_KEY_ID', '')
AMAZON_SECRET_ACCESS_KEY = env('AMAZON_SECRET_ACCESS_KEY', '')
AMAZON_REGION = env('AMAZON_REGION', 'us-east-1')
AMAZON_SERVE_DIRECT_LINKS = env('AMAZON_SERVE_DIRECT_LINKS', False)
AMAZON_S3_USE_HTTPS = env('AMAZON_S3_USE_HTTPS', False)

XML = False
PUBLIC_RESOURCES = []
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'
