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

"""Superdesk default settings, those can be overriden via settings file in project or env variable.

Environment variables names match config name, with some expections documented below.
"""
import json
import os
import pytz
import tzlocal
from urllib.parse import urlparse

from datetime import timedelta, datetime
from celery.schedules import crontab
from kombu import Queue, Exchange
from distutils.util import strtobool as _strtobool


def strtobool(value):
    try:
        return bool(_strtobool(value))
    except ValueError:
        return False


def env(variable, fallback_value=None):
    if os.environ.get("SUPERDESK_USE_DEFAULTS"):
        return fallback_value

    env_value = os.environ.get(variable)
    if env_value is None:
        return fallback_value
    # Next isn't needed anymore
    elif env_value == "__EMPTY__":
        return ""
    else:
        return env_value


def celery_queue(name):
    """Get celery queue name with optional prefix set in environment.

    If you want to use multiple workers in Procfile you have to use the prefix::

        work_publish: celery -A worker -Q "${SUPERDESK_CELERY_PREFIX}publish" worker
        work_default: celery -A worker worker

    :param name: queue name
    """
    return "{}{}".format(os.environ.get("SUPERDESK_CELERY_PREFIX", ""), name)


#: Default TimeZone, will try to guess from server settings if not set
DEFAULT_TIMEZONE = env("DEFAULT_TIMEZONE")

if DEFAULT_TIMEZONE is None:
    DEFAULT_TIMEZONE = tzlocal.get_localzone().zone

if not DEFAULT_TIMEZONE:
    raise ValueError("DEFAULT_TIMEZONE is empty")


def local_to_utc_hour(hour):
    now = datetime.now()
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    local = tz.localize(now.replace(hour=hour))
    return local.utctimetuple()[3]


ABS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
BEHAVE_TESTS_FIXTURES_PATH = ABS_PATH + "/features/steps/fixtures"

IF_MATCH = True
BANDWIDTH_SAVER = False
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S+0000"
ELASTIC_DATE_FORMAT = "%Y-%m-%d"
ELASTIC_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
#: default size of elastic queries generated on server
#: for saved search reports etc.
#:
#: .. versionadded:: 1.34
#:
ELASTIC_DEFAULT_SIZE = 10
PAGINATION_LIMIT = 200

MERGE_NESTED_DOCUMENTS = False

#: keep default in sync with limit - so when client does not use pagination return all
#:
#: .. versionadded:: 1.33
#:
PAGINATION_DEFAULT = PAGINATION_LIMIT

LOG_CONFIG_FILE = env("LOG_CONFIG_FILE", "logging_config.yml")
LOG_SERVER_ADDRESS = env("LOG_SERVER_ADDRESS", "localhost")
LOG_SERVER_PORT = int(env("LOG_SERVER_PORT", 5555))

#: application name - used in email footers, ``APP_NAME`` env
APPLICATION_NAME = env("APP_NAME", "Superdesk")
#: public client url - used to create links within emails etc, ``SUPERDESK_CLIENT_URL`` env
CLIENT_URL = env("SUPERDESK_CLIENT_URL", "http://localhost:9000")

SERVER_URL = env("SUPERDESK_URL", "http://localhost:5000/api")
server_url = urlparse(SERVER_URL)
SERVER_DOMAIN = server_url.netloc or "localhost"
URL_PREFIX = env("URL_PREFIX", server_url.path.lstrip("/")) or ""

# map package name => github repo name, to be filled when a custom version of a package is used
REPO_OVERRIDE = {}

JSON_SORT_KEYS = False
VALIDATION_ERROR_STATUS = 400
VALIDATION_ERROR_AS_LIST = True

CACHE_CONTROL = "max-age=0, no-cache"

X_DOMAINS = "*"
X_MAX_AGE = 24 * 3600
X_HEADERS = ["Content-Type", "Authorization", "If-Match"]

#: mongo db name, only used when mongo_uri is not set
MONGO_DBNAME = env("MONGO_DBNAME", "superdesk")

#: full mongodb connection uri, overrides ``MONGO_DBNAME`` if set
MONGO_URI = env("MONGO_URI", "mongodb://localhost/%s" % MONGO_DBNAME)

#: allow all mongo queries
MONGO_QUERY_BLACKLIST = []

#: legal archive switch
LEGAL_ARCHIVE = env("LEGAL_ARCHIVE", None)

#: legal archive db name
LEGAL_ARCHIVE_DBNAME = env("LEGAL_ARCHIVE_DBNAME", "legal_archive")

#: legal archive mongodb uri
LEGAL_ARCHIVE_URI = env("LEGAL_ARCHIVE_URI", "mongodb://localhost/%s" % LEGAL_ARCHIVE_DBNAME)

#: archived mongodb db name
ARCHIVED_DBNAME = env("ARCHIVED_DBNAME", "archived")

#: archived mongodb uri
ARCHIVED_URI = env("ARCHIVED_URI", "mongodb://localhost/%s" % ARCHIVED_DBNAME)

CONTENTAPI_MONGO_DBNAME = "contentapi"
CONTENTAPI_MONGO_URI = env("CONTENTAPI_MONGO_URI", "mongodb://localhost/%s" % CONTENTAPI_MONGO_DBNAME)

#: elastic url
ELASTICSEARCH_URL = env("ELASTICSEARCH_URL", "http://localhost:9200")
CONTENTAPI_ELASTICSEARCH_URL = env("CONTENTAPI_ELASTICSEARCH_URL", ELASTICSEARCH_URL)

#: elastic index name
ELASTICSEARCH_INDEX = env("ELASTICSEARCH_INDEX", "superdesk")
CONTENTAPI_ELASTICSEARCH_INDEX = env("CONTENTAPI_ELASTICSEARCH_INDEX", CONTENTAPI_MONGO_DBNAME)

if env("ELASTIC_PORT"):
    ELASTICSEARCH_URL = env("ELASTIC_PORT").replace("tcp:", "http:")

ELASTICSEARCH_BACKUPS_PATH = env("ELASTICSEARCH_BACKUPS_PATH", "")

#: elastic settings - superdesk custom filter
ELASTICSEARCH_SETTINGS = {
    "settings": {
        "analysis": {
            "filter": {"remove_hyphen": {"pattern": "[-]", "type": "pattern_replace", "replacement": " "}},
            "char_filter": {
                # https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-charfilters.html
                # https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-htmlstrip-charfilter.html
                "html_strip_filter": {"type": "html_strip"}
            },
            "analyzer": {
                "phrase_prefix_analyzer": {
                    "type": "custom",
                    "filter": ["remove_hyphen", "lowercase"],
                    "tokenizer": "keyword",
                },
                "html_field_analyzer": {
                    "type": "custom",
                    "filter": ["lowercase"],
                    "tokenizer": "standard",
                    "char_filter": ["html_strip_filter"],
                },
            },
        }
    }
}

CONTENTAPI_ELASTICSEARCH_SETTINGS = {
    "settings": {
        "analysis": {
            "char_filter": {"html_strip_filter": {"type": "html_strip"}},
            "analyzer": {
                "html_field_analyzer": {
                    "type": "custom",
                    "filter": ["lowercase"],
                    "tokenizer": "standard",
                    "char_filter": ["html_strip_filter"],
                }
            },
        }
    }
}

# https://www.elastic.co/guide/en/elasticsearch/reference/master/search-request-body.html#request-body-search-track-total-hits # NOQA
ELASTICSEARCH_TRACK_TOTAL_HITS = True

#: redis url
REDIS_URL = env("REDIS_URL", "redis://localhost:6379")
if env("REDIS_PORT"):
    REDIS_URL = env("REDIS_PORT").replace("tcp:", "redis:")

#: cache url - superdesk will try to figure out if it's redis or memcached
CACHE_URL = env("SUPERDESK_CACHE_URL", REDIS_URL)

#: celery broker
BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_BROKER_URL = BROKER_URL

#: celery task config
CELERY_TASK_ALWAYS_EAGER = strtobool(env("CELERY_ALWAYS_EAGER", "false"))
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_PROTOCOL = 1
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_SEND_EVENTS = False

#: celery worker config
CELERY_WORKER_DISABLE_RATE_LIMITS = True
CELERY_WORKER_TASK_SOFT_TIME_LIMIT = 300
CELERY_WORKER_LOG_FORMAT = "%(message)s level=%(levelname)s process=%(processName)s"
CELERY_WORKER_TASK_LOG_FORMAT = " ".join([CELERY_WORKER_LOG_FORMAT, "task=%(task_name)s task_id=%(task_id)s"])
CELERY_WORKER_CONCURRENCY = env("CELERY_WORKER_CONCURRENCY") or None
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

#: celery routing config
CELERY_TASK_DEFAULT_QUEUE = celery_queue("default")
CELERY_TASK_DEFAULT_EXCHANGE = celery_queue("default")
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"

HIGH_PRIORITY_QUEUE = celery_queue("publish_priority")
HIGH_PRIORITY_QUEUE_ENABLED = False

CELERY_TASK_QUEUES = (
    Queue(celery_queue("default"), Exchange(celery_queue("default")), routing_key="default"),
    Queue(celery_queue("expiry"), Exchange(celery_queue("expiry"), type="topic"), routing_key="expiry.#"),
    Queue(celery_queue("legal"), Exchange(celery_queue("legal"), type="topic"), routing_key="legal.#"),
    Queue(celery_queue("ingest"), Exchange(celery_queue("ingest"), type="topic"), routing_key="ingest.#"),
    Queue(celery_queue("publish"), Exchange(celery_queue("publish"), type="topic"), routing_key="publish.#"),
    Queue(
        HIGH_PRIORITY_QUEUE,
        Exchange(HIGH_PRIORITY_QUEUE, type="direct"),
        routing_key=HIGH_PRIORITY_QUEUE,
    ),
)

CELERY_TASK_ROUTES = {
    "apps.archive.content_expiry": {"queue": celery_queue("expiry"), "routing_key": "expiry.content"},
    "superdesk.io.gc_ingest": {
        "queue": celery_queue("expiry"),
        "routing_key": "expiry.ingest",
    },
    "superdesk.io.*": {
        "queue": celery_queue("ingest"),
        "routing_key": "ingest.ingest",
    },
    "superdesk.audit.gc_audit": {"queue": celery_queue("expiry"), "routing_key": "expiry.audit"},
    "apps.auth.session_purge": {"queue": celery_queue("expiry"), "routing_key": "expiry.session"},
    "superdesk.commands.remove_exported_files": {"queue": celery_queue("expiry"), "routing_key": "expiry.temp_files"},
    "content_api.commands.item_expiry": {"queue": celery_queue("expiry"), "routing_key": "expiry.content_api"},
    "apps.legal_archive.*": {"queue": celery_queue("legal"), "routing_key": "legal.publish_queue"},
    "superdesk.publish.*": {"queue": celery_queue("publish"), "routing_key": "publish.transmit"},
    "apps.publish.enqueue.enqueue_published": {"queue": celery_queue("publish"), "routing_key": "publish.enqueue"},
}

#: celery beat config
CELERY_BEAT_SCHEDULE_FILENAME = env("CELERYBEAT_SCHEDULE_FILENAME", "./celerybeatschedule.db")
CELERY_BEAT_SCHEDULE = {
    "ingest:update": {
        "task": "superdesk.io.update_ingest",
        # there is internal schedule for updates per provider,
        # so this is minimal interval when an update can occur
        "schedule": timedelta(seconds=30),
        "options": {"expires": 29},
    },
    "ingest:gc": {
        "task": "superdesk.io.gc_ingest",
        "schedule": timedelta(minutes=5),
    },
    "audit:gc": {"task": "superdesk.audit.gc_audit", "schedule": crontab(minute="0", hour=local_to_utc_hour(1))},
    "session:gc": {"task": "apps.auth.session_purge", "schedule": timedelta(minutes=5)},
    "content:gc": {"task": "apps.archive.content_expiry", "schedule": crontab(minute="*/30")},
    "temp_files:gc": {
        "task": "superdesk.commands.temp_file_expiry",
        "schedule": crontab(minute="0", hour=local_to_utc_hour(3)),
    },
    "content_api:gc": {
        "task": "content_api.commands.item_expiry",
        "schedule": crontab(minute="0", hour=local_to_utc_hour(2)),
    },
    "publish:transmit": {"task": "superdesk.publish.transmit", "schedule": timedelta(seconds=10)},
    "content:schedule": {
        "task": "apps.templates.content_templates.create_scheduled_content",
        "schedule": crontab(minute="*/5"),
    },
    "legal:import_publish_queue": {
        "task": "apps.legal_archive.import_legal_publish_queue",
        "schedule": timedelta(minutes=5),
    },
    "publish:enqueue": {"task": "apps.publish.enqueue.enqueue_published", "schedule": timedelta(seconds=10)},
    "legal:import_legal_archive": {
        "task": "apps.legal_archive.import_legal_archive",
        "schedule": crontab(minute=30, hour=local_to_utc_hour(0)),
    },
    "saved_searches:report": {
        "task": "apps.saved_searches.report",
        "schedule": crontab(minute=0),
    },
}

#: Sentry DSN - will report exceptions there
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_INCLUDE_PATHS = ["superdesk", "apps"]

CORE_APPS = [
    "apps.auth",
    "superdesk.roles",
    "superdesk.storage",
    "superdesk.allowed_values",
    "apps.picture_crop",
    "apps.picture_renditions",
    "apps.video_edit",
    "content_api.publish",
    "content_api.items",
    "content_api.tokens",
    "content_api.items_versions",
    "content_api.api_audit",
    "content_api.search",
    "superdesk.backend_meta",
    "superdesk.server_config",
    "superdesk.internal_destinations",
    "apps.client_config",
    "superdesk.auth",
    "superdesk.auth.oauth",
    "superdesk.attachments",
    "superdesk.auth_server",
    "apps.links",
    "superdesk.locales",
]

#: Specify what modules should be enabled
INSTALLED_APPS = []

#: LDAP Server (eg: ldap://sourcefabric.org)
LDAP_SERVER = env("LDAP_SERVER", "")
#: LDAP Server port
LDAP_SERVER_PORT = int(env("LDAP_SERVER_PORT", 389))

#: Fully Qualified Domain Name. Ex: sourcefabric.org
LDAP_FQDN = env("LDAP_FQDN", "")

#: LDAP_BASE_FILTER limit the base filter to the security group. Ex: OU=Superdesk Users,dc=sourcefabric,dc=org
LDAP_BASE_FILTER = env("LDAP_BASE_FILTER", "")

#: change the user depending on the LDAP directory structure
LDAP_USER_FILTER = env("LDAP_USER_FILTER", "(&(objectCategory=user)(objectClass=user)(sAMAccountName={}))")

#: LDAP User Attributes to fetch. Keys would be LDAP Attribute Name and Value would be Supderdesk Model Attribute Name
LDAP_USER_ATTRIBUTES = json.loads(
    env(
        "LDAP_USER_ATTRIBUTES",
        '{"givenName": "first_name", "sn": "last_name", '
        '"displayName": "display_name", "mail": "email", '
        '"ipPhone": "phone"}',
    )
)

#: Enable the ability for the display name of the user to be overridden with Superdesk user attributes
LDAP_SET_DISPLAY_NAME = strtobool(env("LDAP_SET_DISPLAY_NAME", "False"))
#: List of Superdesk user attributes passed to the format method
LDAP_SET_DISPLAY_NAME_FIELDS = json.loads(env("LDAP_SET_DISPLAY_NAME_FIELDS", '["first_name", "last_name"]'))
#: Format for the user display name
LDAP_SET_DISPLAY_NAME_FORMAT = env("LDAP_SET_DISPLAY_NAME_FORMAT", "{} {}")

if LDAP_SERVER:
    CORE_APPS.append("apps.ldap")
else:
    CORE_APPS.append("superdesk.users")
    CORE_APPS.append("apps.auth.db")
    CORE_APPS.append("apps.auth.xmpp")
    CORE_APPS.append("apps.auth.oidc")


CORE_APPS.extend(
    [
        "superdesk.upload",
        "superdesk.download",
        "superdesk.sequences",
        "superdesk.notification",
        "superdesk.data_updates",
        "superdesk.activity",
        "superdesk.audit",
        "superdesk.vocabularies",
        "apps.comments",
        "superdesk.profiling",
        "superdesk.io",
        "superdesk.io.feeding_services",
        "superdesk.io.feed_parsers",
        "superdesk.io.webhooks",
        "superdesk.io.subjectcodes",
        "superdesk.io.format_document_for_preview",
        "superdesk.io.iptc",
        "superdesk.io.mediatopics",
        "superdesk.text_checkers.spellcheckers",
        "superdesk.text_checkers.ai",
        "apps.io",
        "apps.io.feeding_services",
        "superdesk.publish",
        "superdesk.commands",
        "superdesk.locators",
        "superdesk.media",
        "apps.auth",
        "apps.archive",
        "apps.archive.item_comments",
        "apps.archive.autocomplete",
        "apps.archive_history",
        "apps.stages",
        "apps.desks",
        "apps.tasks",
        "apps.preferences",
        "apps.spikes",
        "apps.prepopulate",
        "apps.legal_archive",
        "apps.search",
        "apps.saved_searches",
        "apps.suggestions",
        "apps.privilege",
        "apps.rules",
        "apps.highlights",
        "apps.marked_desks",
        "apps.products",
        "apps.publish",
        "apps.export",
        "apps.publish.formatters",
        "apps.content_filters",
        "apps.content_types",
        "apps.dictionaries",
        "apps.duplication",
        "apps.spellcheck",
        "apps.templates",
        "apps.archived",
        "apps.validators",
        "apps.validate",
        "apps.workspace",
        "apps.macros",
        "apps.archive_broadcast",
        "apps.search_providers",
        "apps.feature_preview",
        "apps.workqueue",
        "apps.contacts",
        "apps.monitoring",
        "apps.concept_items",
        "superdesk.places",
        "apps.desk_routing",
    ]
)

RESOURCE_METHODS = ["GET", "POST"]
ITEM_METHODS = ["GET", "PATCH", "PUT", "DELETE"]
EXTENDED_MEDIA_INFO = ["content_type", "name", "length", "_id"]
RETURN_MEDIA_AS_BASE64_STRING = False
VERSION = "_current_version"

#: uses for generation of media url ``(<media_prefix>/<media_id>)``::
MEDIA_PREFIX = env("MEDIA_PREFIX", "%s/upload-raw" % SERVER_URL.rstrip("/"))
MEDIA_PREFIXES_TO_FIX = None

#: amazon access key
AMAZON_ACCESS_KEY_ID = env("AMAZON_ACCESS_KEY_ID", "")
#: amazon secret access key
AMAZON_SECRET_ACCESS_KEY = env("AMAZON_SECRET_ACCESS_KEY", "")
#: amazon region
AMAZON_REGION = env("AMAZON_REGION", "us-east-1")
#: amazon bucket name
AMAZON_CONTAINER_NAME = env("AMAZON_CONTAINER_NAME", "")
#: use subfolder in bucket to store files
AMAZON_S3_SUBFOLDER = env("AMAZON_S3_SUBFOLDER", "")
#: adds ACL when putting to S3, can be set to ``public-read``, etc.
AMAZON_OBJECT_ACL = env("AMAZON_OBJECT_ACL", "")
#: amazon endpoint. This can be used with third-party s3-compatible servers
AMAZON_ENDPOINT_URL = env("AMAZON_ENDPOINT_URL", "")

RENDITIONS = {
    "picture": {
        "thumbnail": {"width": 220, "height": 120},
        "viewImage": {"width": 640, "height": 640},
        "baseImage": {"width": 1400, "height": 1400},
    },
    "avatar": {
        "thumbnail": {"width": 60, "height": 60},
        "viewImage": {"width": 200, "height": 200},
    },
}


#: BCRYPT work factor
BCRYPT_GENSALT_WORK_FACTOR = 12

#: The number of days a token is valid, env ``RESET_PASS_TTL``
RESET_PASSWORD_TOKEN_TIME_TO_LIVE = int(env("RESET_PASS_TTL", 1))
#: The number of days an activation token is valid, env ``ACTIVATE_TTL``
ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE = int(env("ACTIVATE_TTL", 7))

#: email server url
MAIL_SERVER = env("MAIL_SERVER", "localhost")
#: email server port
MAIL_PORT = int(env("MAIL_PORT", 25))
#: use tls connection
MAIL_USE_TLS = strtobool(env("MAIL_USE_TLS", "False"))
#: use ssl connection
MAIL_USE_SSL = strtobool(env("MAIL_USE_SSL", "False"))
#: email account username
MAIL_USERNAME = env("MAIL_USERNAME", "")
#: email account password
MAIL_PASSWORD = env("MAIL_PASSWORD", "")
#: default sender for superdesk emails
MAIL_DEFAULT_SENDER = MAIL_USERNAME or "superdesk@localhost"

_MAIL_FROM = env("MAIL_FROM", MAIL_USERNAME)

#: list of admin emails - get error notifications by default
ADMINS = [_MAIL_FROM]

DEBUG = strtobool(env("SUPERDESK_DEBUG", "false"))
SUPERDESK_TESTING = strtobool(env("SUPERDESK_TESTING", "false"))

#: Set the timezone celery functions to UTC to avoid daylight savings issues SDESK-1057
CELERY_TIMEZONE = "UTC"

#: The number of days after the user has to change his password
PASSWORD_EXPIRY_DAYS = int(env("PASSWORD_EXPIRY_DAYS", 0))

#: The number of minutes since the last update of the Mongo auth object after which it will be deleted
SESSION_EXPIRY_MINUTES = int(env("SESSION_EXPIRY_MINUTES", 240))

#: The number of minutes before content items are purged
CONTENT_EXPIRY_MINUTES = int(env("CONTENT_EXPIRY_MINUTES", 0))

#: The number of minutes before content items are purged from archived
#:
#: .. versionadded:: 1.34
#:
ARCHIVED_EXPIRY_MINUTES = int(env("ARCHIVED_EXPIRY_MINUTES", 0))

#: The number of minutes before ingest items are purged
INGEST_EXPIRY_MINUTES = int(env("INGEST_EXPIRY_MINUTES", 2 * 24 * 60))

#: The number of minutes before published content items are purged
PUBLISHED_CONTENT_EXPIRY_MINUTES = int(env("PUBLISHED_CONTENT_EXPIRY_MINUTES", 0))

#: The number of minutes before audit content is purged
AUDIT_EXPIRY_MINUTES = int(env("AUDIT_EXPIRY_MINUTES", 0))

#: The number records to be fetched for expiry.
MAX_EXPIRY_QUERY_LIMIT = int(env("MAX_EXPIRY_QUERY_LIMIT", 100))

#: The number of minutes before Publish Queue is purged
PUBLISH_QUEUE_EXPIRY_MINUTES = int(env("PUBLISH_QUEUE_EXPIRY_MINUTES", 0))

# This setting can be used to apply a limit on the elastic search queries, it is a limit per shard.
# A value of -1 indicates that no limit will be applied.
# If for example the elastic has 5 shards and you wish to limit the number of search results to 1000 then set the value
# to 200 (1000/5).
MAX_SEARCH_DEPTH = int(env("MAX_SEARCH_DEPTH", -1))

#: Defines the maximum value of Ingest Sequence Number after which the value will start from 1
MAX_VALUE_OF_INGEST_SEQUENCE = int(env("MAX_VALUE_OF_INGEST_SEQUENCE", 9999))

DAYS_TO_KEEP = int(env("INGEST_ARTICLES_TTL", "2"))

MACROS_MODULE = env("MACROS_MODULE", "superdesk.macros")

WS_HOST = env("WSHOST", "0.0.0.0")
WS_PORT = env("WSPORT", "5100")

# Used by the  Kombu Connection. Only valid for the AMQP protocol
WS_HEART_BEAT = int(env("WS_HEARTBEAT", "0"))

#: Defines the maximum value of Publish Sequence Number after which the value will start from 1
MAX_VALUE_OF_PUBLISH_SEQUENCE = int(env("MAX_VALUE_OF_PUBLISH_SEQUENCE", 9999))

#: Defines default value for Source to be set for manually created articles
DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES = env("DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES", "Superdesk")

#: Defines default value for Priority to be set for manually created articles
DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES = int(env("DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES", 6))

#: Defines default value for Urgency to be set for manually created articles
DEFAULT_URGENCY_VALUE_FOR_MANUAL_ARTICLES = int(env("DEFAULT_URGENCY_VALUE_FOR_MANUAL_ARTICLES", 3))

#: Defines default value for genre to be set for manually created articles
DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES = env(
    "DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES", [{"qcode": "Article", "name": "Article (news)"}]
)

#: Defines default qcodes (comma separated) for category for ingested and auto published articles
DEFAULT_CATEGORY_QCODES_FOR_AUTO_PUBLISHED_ARTICLES = env("DEFAULT_CATEGORY_QCODES_FOR_AUTO_PUBLISHED_ARTICLES", "a")

#: Defines default value for Priority to be set for ingested articles
DEFAULT_PRIORITY_VALUE_FOR_INGESTED_ARTICLES = int(env("DEFAULT_PRIORITY_VALUE_FOR_INGESTED_ARTICLES", 6))

#: Defines default value for Urgency to be set for ingested articles
DEFAULT_URGENCY_VALUE_FOR_INGESTED_ARTICLES = int(env("DEFAULT_URGENCY_VALUE_FOR_INGESTED_ARTICLES", 3))

#: Defines default value for Priority to be reset for update articles SD-4595
RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES = strtobool(env("RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES", "False"))

#: Determines if the ODBC publishing mechanism will be used, If enabled then pyodbc must be installed along with it's
#: dependencies
ODBC_PUBLISH = env("ODBC_PUBLISH", None)

# ODBC test server connection string
ODBC_TEST_CONNECTION_STRING = env(
    "ODBC_TEST_CONNECTION_STRING", "DRIVER=FreeTDS;DSN=NEWSDB;UID=???;PWD=???;DATABASE=News"
)

#: This value gets injected into NewsML 1.2 and G2 output documents.
NEWSML_PROVIDER_ID = env("NEWSML_PROVIDER_ID", "sourcefabric.org")
#: This value gets injected into NewsML 1.2 and G2 output documents.
ORGANIZATION_NAME = env("ORGANIZATION_NAME", "Your organisation")
#: This value gets injected into NewsML 1.2 and G2 output documents.
ORGANIZATION_NAME_ABBREVIATION = env("ORGANIZATION_NAME_ABBREVIATION", "Short name for your organisation")

#: max retries when transmitting an item
MAX_TRANSMIT_RETRY_ATTEMPT = int(env("MAX_TRANSMIT_RETRY_ATTEMPT", 10))

#: delay between retry attempts
TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES = int(env("TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES", 3))

#: max transmit items to be fetched from mongo at once
MAX_TRANSMIT_QUERY_LIMIT = int(env("MAX_TRANSMIT_QUERY_LIMIT", 500))

#: Code profiling for performance analysis
ENABLE_PROFILING = False

#: default timeout for ftp connections
FTP_TIMEOUT = 300

#: default timeout when publishing using the `http_push` transmitter
HTTP_PUSH_TIMEOUT = (5, 30)

#: default amount of files which can processed during one iteration of ftp ingest
FTP_INGEST_FILES_LIST_LIMIT = 100

#: after how many minutes consider content to be too old for ingestion
#:
#: .. versionadded:: 1.32.2
#:
INGEST_OLD_CONTENT_MINUTES = 10

#: default timeout for email connections
EMAIL_TIMEOUT = 10

#: This setting is used to overide the desk/stage expiry for items when spiked
SPIKE_EXPIRY_MINUTES = None

SECRET_KEY = env("SECRET_KEY", "")

#: secure login
XMPP_AUTH_URL = env("XMPP_AUTH_URL", "")
XMPP_AUTH_DOMAIN = env("XMPP_AUTH_DOMAIN", "Superdesk")

#: copies basic metadata from parent of associated items
COPY_METADATA_FROM_PARENT = strtobool(env("COPY_METADATA_FROM_PARENT", "false"))

#: The number of hours before temporary media files are purged
TEMP_FILE_EXPIRY_HOURS = int(env("TEMP_FILE_EXPIRY_HOURS", 24))

#: The number of days before content api items are removed. Defaults to 0 which means no purging occurs
CONTENT_API_EXPIRY_DAYS = int(env("CONTENT_API_EXPIRY_DAYS", 0))

# Google OAuth settings
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
# Google login will only be activated if both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set
GOOGLE_LOGIN = True
GOOGLE_GMAIL = True


# SAML Auth settings
SAML_PATH = env("SAML_PATH")
SAML_LABEL = env("SAML_LABEL", "Single Sign On")

EXCLUDED_VOCABULARY_FIELDS = [
    "default_categories",
    "signal",
    "rightsinfo",
    "subscriber_types",
    "crop_sizes",
    "desk_types",
    "replace_words",
    "locators",
    "product_types",
    "author_roles",
    "job_titles",
]


#: allows overriding default schema by type, use picture/composite/text keys
SCHEMA = {}
EDITOR = {}

# editor note overriding
#: set to False if you don't want overriding on correction
OVERRIDE_EDNOTE_FOR_CORRECTIONS = True
#: template to use for overriding, you can use {date} and {slugline} placeholders
#: if not set, a default template will be used
# OVERRIDE_EDNOTE_TEMPLATE = 'Story "{slugline}" corrected on {date}'

#: allowed HTML tag in client
HTML_TAGS_WHITELIST = (
    "h1",
    "h2",
    "h3",
    "h4",
    "h6",
    "blockquote",
    "pre",
    "figure",
    "ul",
    "ol",
    "li",
    "div",
    "p",
    "em",
    "strong",
    "i",
    "b",
)

# Japanese reading speed
JAPANESE_CHARACTERS_PER_MINUTE = 600

#: publish associated items automatically
PUBLISH_ASSOCIATED_ITEMS = False

#: raise error when published item is not queued to any subscriber
PUBLISH_NOT_QUEUED_ERROR = True

# Use content profile for validation when auto-publishing
AUTO_PUBLISH_CONTENT_PROFILE = True

#: controll error notifications globally
ERROR_NOTIFICATIONS = strtobool(env("SUPERDESK_ERROR_NOTIFICATIONS", "true"))

#: geonames config
GEONAMES_USERNAME = env("GEONAMES_USERNAME")
GEONAMES_TOKEN = env("GEONAMES_TOKEN")
GEONAMES_URL = env("GEONAMES_URL", "http://api.geonames.org/")
GEONAMES_FEATURE_CLASSES = ["P"]
#: Set how much metadata should be returned
#:
#: .. versionadded:: 1.33
#:
GEONAMES_SEARCH_STYLE = "medium"

# media required fields
VALIDATOR_MEDIA_METADATA = {
    "headline": {
        "required": True,
    },
    "alt_text": {
        "required": True,
    },
    "archive_description": {
        "required": False,
    },
    "description_text": {
        "required": True,
        "textarea": True,
    },
    "copyrightholder": {
        "required": False,
    },
    "byline": {
        "required": False,
    },
    "usageterms": {
        "required": False,
    },
    "copyrightnotice": {
        "required": False,
    },
}

#: Allows you to disable validation on publish using these,
#: but they will still be checked by client on upload.
#:
#: .. versionadded:: 1.34
#:
VALIDATE_MEDIA_METADATA_ON_PUBLISH = True

#: Behaviour on missing vocabulary, only used in (STT)NewsML G2 for now
#: if "reject", missing vocabulary are rejected
#: if "create", a new vocabulary is created
#: if "continue" (default), value is returned but not created (it will be present in the resulting item, but the
#: missing vocabulary is not added to SD)

QCODE_MISSING_VOC = "continue"

# Relative path and filename for an image to apply as a watermark on publish of feature media via email.
WATERMARK_IMAGE = env("WATERMARK_IMAGE", "")


#: Kill template config
KILL_TEMPLATE_NULL_FIELDS = ["byline", "place"]

#: Video editor server
VIDEO_SERVER_URL = env("VIDEO_SERVER_URL", "http://localhost:5050")
VIDEO_SERVER_ENABLED = strtobool(env("VIDEO_SERVER_ENABLED", "false"))

#: Whether to generate custom crops on image upload by default or not, if false means generate else don't generate
NO_CUSTOM_CROPS = strtobool(env("NO_CUSTOM_CROPS", "false"))

#: Authorisation server

#: how long an authorisation token is valid (in seconds)
AUTH_SERVER_EXPIRATION_DELAY = env("AUTH_SERVER_EXPIRATION_TIME", 60 * 60 * 24)  # 1 day by default
AUTH_SERVER_SHARED_SECRET = env("AUTH_SERVER_SHARED_SECRET", "")

#: Add missing keywords to *keywords* vocabulary when item is published
#:
#: .. versionadded:: 2.0
#:
KEYWORDS_ADD_MISSING_ON_PUBLISH = False

#: Allow creating multiple updates in production
#:
#: By default there can be only 1 update in progress
#: for a story, when enable there is no limit and multiple
#: updates can be created. It will still validate on publish
#: if the previous ones are published and not let publishing
#: out of sequence.
#:
#: .. versionadded:: 2.0
#:
WORKFLOW_ALLOW_MULTIPLE_UPDATES = False

#: Allow users who are not members on a desk to duplicate its content
#:
#: .. versionadded:: 1.34
#:
WORKFLOW_ALLOW_DUPLICATE_TO_NON_MEMBERS = False

#: Allow users to copy content from desk to personal
#:
#: .. versionadded:: 1.34
#:
WORKFLOW_ALLOW_COPY_TO_PERSONAL = True

#: Enable archive autocomplete API
#:
#: .. versionadded:: 2.0
#:
#: It will return suggestions for field from archive api,
#: only from published items for time defined via
#: :data:`ARCHIVE_AUTOCOMPLETE_DAYS` and :data:`ARCHIVE_AUTOCOMPLETE_HOURS`.
#:
ARCHIVE_AUTOCOMPLETE = False

#:
#: .. versionadded:: 2.0
#:
ARCHIVE_AUTOCOMPLETE_DAYS = 0

#:
#: .. versionadded:: 2.0
#:
ARCHIVE_AUTOCOMPLETE_HOURS = 0


#: Tansa client config
#:
#: .. versionadded:: 2.0
#:
TANSA_APP_ID = env("TANSA_APP_ID")
TANSA_USER_ID = env("TANSA_USER_ID")
TANSA_PROFILE_ID = env("TANSA_PROFILE_ID")
TANSA_LICENSE_KEY = env("TANSA_LICENSE_KEY")
TANSA_CLIENT_BASE_URL = env("TANSA_CLIENT_BASE_URL", "https://d02.tansa.com/tansaclient/")
TANSA_PROFILES = {}

# Enable ninjs to send all the fields for place in output.
NINJS_PLACE_EXTENDED = False

#: Define for how many hours in the past it shoudl return links for.
#:
#: Set to `0` to disable time limit.
#:
#: .. versionadded:: 1.34
#:
LINKS_MAX_HOURS = 0

#: Set if missing users can be created automatically
#:
#: when using external authentication service
#:
#: .. versionadded:: 2.0
USER_EXTERNAL_CREATE = False

#: Desk to which external users will be assigned automatically.
#:
#: .. versionadded:: 2.0
#:
USER_EXTERNAL_DESK = None

#: Remove domain from username when creating users via sso
#:
#: .. versionadded:: 2.0
#:
USER_EXTERNAL_USERNAME_STRIP_DOMAIN = False

#: Set regex pattern to check username for
#:
#: .. versionadded:: 2.0
#:
USER_USERNAME_PATTERN = None

#: Default instance language
#:
#: .. versionadded:: 2.0
#:
DEFAULT_LANGUAGE = "en"

#: OIDC config
#:
#: .. versionadded:: 2.1
#:
OIDC_ENABLED = strtobool(env("OIDC_ENABLED", "false"))
OIDC_ISSUER_URL = env("OIDC_ISSUER_URL", "http://localhost:8080/auth/realms/SUPERDESK_REALM")
OIDC_SERVER_CLIENT = env("OIDC_SERVER_CLIENT")
OIDC_SERVER_CLIENT_SECRET = env("OIDC_SERVER_CLIENT_SECRET")
OIDC_WEB_CLIENT = env("OIDC_WEB_CLIENT")
OIDC_BROWSER_REDIRECT_URL = env("OIDC_BROWSER_REDIRECT_URL", CLIENT_URL)

#: Data update paths defined by apps
#:
#: .. versionadded:: 2.1
#:
APPS_DATA_UPDATES_PATHS = []
