Configuration
=============

.. module:: superdesk.default_settings

We use ``flask.app.config``, so to use it do::

    from flask import current_app as app

    print(app.config['SERVER_NAME'])

Configuration is combination of default settings module and settings module
in `application repo <https://github.com/superdesk/superdesk/blob/master/server/settings.py>`_.

Default settings
----------------

.. automodule:: superdesk.default_settings

General settings
^^^^^^^^^^^^^^^^

.. autodata:: APPLICATION_NAME
.. autodata:: SERVER_NAME
.. autodata:: CLIENT_URL

.. autodata:: INSTALLED_APPS

.. autodata:: DEFAULT_TIMEZONE

.. autodata:: FTP_TIMEOUT
.. autodata:: ENABLE_PROFILING

Content settings
^^^^^^^^^^^^^^^^

.. autodata:: CONTENT_EXPIRY_MINUTES
.. autodata:: INGEST_EXPIRY_MINUTES
.. autodata:: SPIKE_EXPIRY_MINUTES

.. autodata:: MAX_VALUE_OF_INGEST_SEQUENCE
.. autodata:: MAX_VALUE_OF_PUBLISH_SEQUENCE

.. autodata:: DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES
.. autodata:: DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES
.. autodata:: DEFAULT_URGENCY_VALUE_FOR_MANUAL_ARTICLES
.. autodata:: DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES
.. autodata:: DEFAULT_PRIORITY_VALUE_FOR_INGESTED_ARTICLES
.. autodata:: DEFAULT_URGENCY_VALUE_FOR_INGESTED_ARTICLES
.. autodata:: RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES

.. autodata:: NEWSML_PROVIDER_ID
.. autodata:: ORGANIZATION_NAME
.. autodata:: ORGANIZATION_NAME_ABBREVIATION

.. autodata:: NO_TAKES

Publish settings
^^^^^^^^^^^^^^^^

.. autodata:: MAX_TRANSMIT_RETRY_ATTEMPT
.. autodata:: TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES
.. autodata:: MAX_TRANSMIT_QUERY_LIMIT

.. autodata:: ODBC_PUBLISH

Mongo connections
^^^^^^^^^^^^^^^^^

There are multiple connections by default, so that it can use different instances for legal archive
and production content.

For each there is ``_DBNAME`` and ``_URI`` setting, if ``_URI`` is set it will be used as is, if not it will
use ``localhost`` as server and ``_DBNAME`` as db.

.. autodata:: MONGO_DBNAME
.. autodata:: MONGO_URI

.. autodata:: LEGAL_ARCHIVE_DBNAME
.. autodata:: LEGAL_ARCHIVE_URI

.. autodata:: ARCHIVED_DBNAME
.. autodata:: ARCHIVED_URI

Elastic settings
^^^^^^^^^^^^^^^^

.. autodata:: ELASTICSEARCH_URL
.. autodata:: ELASTICSEARCH_INDEX
.. autodata:: ELASTICSEARCH_SETTINGS

Redis settings
^^^^^^^^^^^^^^

.. autodata:: REDIS_URL

Cache settings
^^^^^^^^^^^^^^

.. autodata:: CACHE_URL

Celery settings
^^^^^^^^^^^^^^^

.. autodata:: BROKER_URL

Monitoring settings
^^^^^^^^^^^^^^^^^^^

.. autodata:: SENTRY_DSN

LDAP settings
^^^^^^^^^^^^^

Used for *LDAP* based authentication, if not configured it will use mongodb for credentials.

.. autodata:: LDAP_SERVER
.. autodata:: LDAP_SERVER_PORT
.. autodata:: LDAP_FQDN
.. autodata:: LDAP_BASE_FILTER
.. autodata:: LDAP_USER_FILTER
.. autodata:: LDAP_USER_ATTRIBUTES

Amazon S3 settings
^^^^^^^^^^^^^^^^^^
.. autodata:: AMAZON_CONTAINER_NAME
.. autodata:: AMAZON_ACCESS_KEY_ID
.. autodata:: AMAZON_SECRET_ACCESS_KEY
.. autodata:: AMAZON_REGION
.. autodata:: AMAZON_SERVE_DIRECT_LINKS
.. autodata:: AMAZON_S3_USE_HTTPS
.. autodata:: AMAZON_SERVER
.. autodata:: AMAZON_PROXY_SERVER

Security settings
^^^^^^^^^^^^^^^^^
.. autodata:: SESSION_EXPIRY_MINUTES
.. autodata:: RESET_PASSWORD_TOKEN_TIME_TO_LIVE
.. autodata:: ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE

Email settings
^^^^^^^^^^^^^^

.. autodata:: MAIL_SERVER
.. autodata:: MAIL_PORT
.. autodata:: MAIL_USE_TLS
.. autodata:: MAIL_USE_SSL
.. autodata:: MAIL_USERNAME
.. autodata:: MAIL_PASSWORD
.. autodata:: MAIL_DEFAULT_SENDER
.. autodata:: ADMINS
