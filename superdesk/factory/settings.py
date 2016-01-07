#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
import json

from datetime import timedelta

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


XML = False
IF_MATCH = True
BANDWIDTH_SAVER = False
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'
PAGINATION_LIMIT = 200

APPLICATION_NAME = env('APP_NAME', 'Superdesk')
server_url = urlparse(env('SUPERDESK_URL', 'http://localhost:5000/api'))
CLIENT_URL = env('SUPERDESK_CLIENT_URL', 'http://localhost:9000')
URL_PROTOCOL = server_url.scheme or None
SERVER_NAME = server_url.netloc or None
URL_PREFIX = server_url.path.lstrip('/') or ''
if SERVER_NAME.endswith(':80'):
    SERVER_NAME = SERVER_NAME[:-3]

VALIDATION_ERROR_STATUS = 400
JSON_SORT_KEYS = True

CACHE_CONTROL = 'max-age=0, no-cache'

X_DOMAINS = '*'
X_MAX_AGE = 24 * 3600
X_HEADERS = ['Content-Type', 'Authorization', 'If-Match']

MONGO_DBNAME = env('MONGO_DBNAME', 'superdesk')
MONGO_URI = env('MONGO_URI', 'mongodb://localhost/%s' % MONGO_DBNAME)

ELASTICSEARCH_URL = env('ELASTICSEARCH_URL', 'http://localhost:9200')
ELASTICSEARCH_INDEX = env('ELASTICSEARCH_INDEX', 'superdesk')
if env('ELASTIC_PORT'):
    ELASTICSEARCH_URL = env('ELASTIC_PORT').replace('tcp:', 'http:')

ELASTICSEARCH_SETTINGS = {
    'settings': {
        'analysis': {
            'filter': {
                'remove_hyphen': {
                    'pattern': '[-]',
                    'type': 'pattern_replace',
                    'replacement': ' '
                }
            },
            'analyzer': {
                'phrase_prefix_analyzer': {
                    'type': 'custom',
                    'filter': ['remove_hyphen', 'lowercase'],
                    'tokenizer': 'keyword'
                }
            }
        }
    }
}

REDIS_URL = env('REDIS_URL', 'redis://localhost:6379')
if env('REDIS_PORT'):
    REDIS_URL = env('REDIS_PORT').replace('tcp:', 'redis:')
BROKER_URL = env('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = BROKER_URL
CELERY_ALWAYS_EAGER = (env('CELERY_ALWAYS_EAGER', False) == 'True')
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['pickle', 'json']  # it's using pickle when in eager mode
CELERY_IGNORE_RESULT = True
CELERY_DISABLE_RATE_LIMITS = True
CELERYD_TASK_SOFT_TIME_LIMIT = 300
CELERYD_LOG_FORMAT = '%(message)s level=%(levelname)s process=%(processName)s'
CELERYD_TASK_LOG_FORMAT = ' '.join([CELERYD_LOG_FORMAT, 'task=%(task_name)s task_id=%(task_id)s'])

CELERYBEAT_SCHEDULE_FILENAME = env('CELERYBEAT_SCHEDULE_FILENAME', './celerybeatschedule.db')
CELERYBEAT_SCHEDULE = {
    'ingest:update': {
        'task': 'superdesk.io.update_ingest',
        # there is internal schedule for updates per provider,
        # so this is minimal interval when an update can occur
        'schedule': timedelta(seconds=30),
        'options': {'expires': 29}
    },
    'ingest:gc': {
        'task': 'superdesk.io.gc_ingest',
        'schedule': timedelta(minutes=5),
    },
    'publish:transmit': {
        'task': 'superdesk.publish.transmit',
        'schedule': timedelta(seconds=10)
    },
}

SENTRY_DSN = env('SENTRY_DSN')
SENTRY_INCLUDE_PATHS = ['superdesk']

INSTALLED_APPS = [
    'superdesk.sequences',
    'superdesk.upload',
    'superdesk.notification',
    'superdesk.activity',
    'superdesk.roles',
    'superdesk.users',

    'superdesk.io',
    'superdesk.io.feeding_services',
    'superdesk.io.feed_parsers',
    'superdesk.io.subjectcodes',
    'superdesk.io.iptc',
    'superdesk.publish',
    'superdesk.commands',
    'superdesk.locators.locators',
    'superdesk.vocabularies',
]

RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']
EXTENDED_MEDIA_INFO = ['content_type', 'name', 'length']
RETURN_MEDIA_AS_BASE64_STRING = False
VERSION = '_current_version'

AMAZON_CONTAINER_NAME = env('AMAZON_CONTAINER_NAME', '')
AMAZON_ACCESS_KEY_ID = env('AMAZON_ACCESS_KEY_ID', '')
AMAZON_SECRET_ACCESS_KEY = env('AMAZON_SECRET_ACCESS_KEY', '')
AMAZON_REGION = env('AMAZON_REGION', 'us-east-1')
AMAZON_SERVE_DIRECT_LINKS = env('AMAZON_SERVE_DIRECT_LINKS', False)
AMAZON_S3_USE_HTTPS = env('AMAZON_S3_USE_HTTPS', False)
AMAZON_SERVER = env('AMAZON_SERVER', 'amazonaws.com')
AMAZON_PROXY_SERVER = env('AMAZON_PROXY_SERVER', None)

RENDITIONS = {
    'picture': {
        'thumbnail': {'width': 220, 'height': 120},
        'viewImage': {'width': 640, 'height': 640},
        'baseImage': {'width': 1400, 'height': 1400},
    },
    'avatar': {
        'thumbnail': {'width': 60, 'height': 60},
        'viewImage': {'width': 200, 'height': 200},
    }
}

SERVER_DOMAIN = 'localhost'

BCRYPT_GENSALT_WORK_FACTOR = 12
RESET_PASSWORD_TOKEN_TIME_TO_LIVE = int(env('RESET_PASS_TTL', 1))  # The number of days a token is valid
# The number of days an activation token is valid
ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE = int(env('ACTIVATE_TTL', 7))

# email server
MAIL_SERVER = env('MAIL_SERVER', 'smtp.googlemail.com')
MAIL_PORT = int(env('MAIL_PORT', 465))
MAIL_USE_TLS = json.loads(env('MAIL_USE_TLS', 'False').lower())
MAIL_USE_SSL = json.loads(env('MAIL_USE_SSL', 'False').lower())
MAIL_USERNAME = env('MAIL_USERNAME', 'admin@sourcefabric.org')
MAIL_PASSWORD = env('MAIL_PASSWORD', '')
ADMINS = [MAIL_USERNAME]

SUPERDESK_TESTING = (env('SUPERDESK_TESTING', 'false').lower() == 'true')

# The number of minutes since the last update of the Mongo auth object after which it will be deleted
SESSION_EXPIRY_MINUTES = 240

# The number of minutes before content items purged
# 2880 = 3 days in minutes
CONTENT_EXPIRY_MINUTES = 4320

# The number of minutes before ingest items purged
# 2880 = 2 days in minutes
INGEST_EXPIRY_MINUTES = int(env('INGEST_EXPIRY_MINUTES', '2880'))

# This setting can be used to apply a limit on the elastic search queries, it is a limit per shard.
# A value of -1 indicates that no limit will be applied.
# If for example the elastic has 5 shards and you wish to limit the number of search results to 1000 then set the value
# to 200 (1000/5).
MAX_SEARCH_DEPTH = -1

# Defines the maximum value of Ingest Sequence Number after which the value will start from 1
MAX_VALUE_OF_INGEST_SEQUENCE = 9999

DAYS_TO_KEEP = int(env('INGEST_ARTICLES_TTL', '2'))

WS_HOST = env('WSHOST', '0.0.0.0')
WS_PORT = env('WSPORT', '5100')

# Defines the maximum value of Publish Sequence Number after which the value will start from 1
MAX_VALUE_OF_PUBLISH_SEQUENCE = 9999

# Defines default value for Source to be set for manually created articles
DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES = env('DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES', 'SPP')

# Determines if the ODBC publishing mechanism will be used, If enabled then pyodbc must be installed along with it's
# dependencies
ODBC_PUBLISH = env('ODBC_PUBLISH', None)
# ODBC test server connection string
ODBC_TEST_CONNECTION_STRING = env('ODBC_TEST_CONNECTION_STRING',
                                  'DRIVER=FreeTDS;DSN=NEWSDB;UID=???;PWD=???;DATABASE=News')

# This value gets injected into NewsML 1.2 and G2 output documents.
NEWSML_PROVIDER_ID = env('NEWSML_PROVIDER_ID', 'sourcefabric.org')

# TODO(Adrian): find a better default
ORGANIZATION_NAME = "Superdesk Powered Press"
ORGANIZATION_NAME_ABBREVIATION = "SPP"
