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

from superdesk.default_settings import SECRET_KEY, MONGO_DBNAME, MONGO_URI  # noqa
from superdesk.default_settings import AMAZON_CONTAINER_NAME, AMAZON_ACCESS_KEY_ID  # noqa
from superdesk.default_settings import AMAZON_SECRET_ACCESS_KEY, AMAZON_REGION  # noqa
from superdesk.default_settings import AMAZON_SERVE_DIRECT_LINKS, AMAZON_S3_USE_HTTPS  # noqa
from superdesk.default_settings import AMAZON_SERVER, AMAZON_PROXY_SERVER, AMAZON_URL_GENERATOR  # noqa


CONTENTAPI_MONGO_DBNAME = 'contentapi'
CONTENTAPI_MONGO_URI = env('CONTENTAPI_MONGO_URI', 'mongodb://localhost/%s' % CONTENTAPI_MONGO_DBNAME)

CONTENTAPI_ELASTICSEARCH_URL = env('CONTENTAPI_ELASTICSEARCH_URL', 'http://localhost:9200')
CONTENTAPI_ELASTICSEARCH_INDEX = env('CONTENTAPI_ELASTICSEARCH_INDEX', CONTENTAPI_MONGO_DBNAME)

CONTENTAPI_INSTALLED_APPS = [
    'content_api.items',
    'content_api.packages',
    'content_api.assets',
]

CONTENTAPI_DOMAIN = {}

# NOTE: no trailing slash for the CONTENTAPI_URL setting!
CONTENTAPI_URL = env('CONTENTAPI_URL', 'http://localhost:5400')
server_url = urlparse(CONTENTAPI_URL)
URL_PREFIX = server_url.path.strip('/')

XML = False
PUBLIC_RESOURCES = []
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'
ELASTIC_DATE_FORMAT = '%Y-%m-%d'
BCRYPT_GENSALT_WORK_FACTOR = 12
