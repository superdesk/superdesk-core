Configuration
=============

We use ``flask.app.config``, so to use it do::

    from flask import current_app as app

    print(app.config['SERVER_NAME'])

Configuration is combination of default settings module and settings module
in `application repo <https://github.com/superdesk/superdesk/blob/master/server/settings.py>`_.

Default settings
----------------

``APPLICATION_NAME``
~~~~~~~~~~~~~~~~~~~~

Default: ``'Superdesk'``

``SERVER_NAME``
~~~~~~~~~~~~~~~

Default: ``'localhost:5000'``

``CLIENT_URL``
~~~~~~~~~~~~~~

Default: ``'http://localhost:9000'``

``DEFAULT_TIMEZONE``
~~~~~~~~~~~~~~~~~~~~

Default: ``None``

Superdesk will try to guess the value from system if not set.

``FTP_TIMEOUT``
~~~~~~~~~~~~~~~

Default: ``300``

This is used for all ftp operations. Increase if you get ftp timeout errors.

``INSTALLED_APPS``
~~~~~~~~~~~~~~~~~~

Default: ``[]``

You can install additional modules by adding their names here.

``CONTENT_EXPIRY_MINUTES``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``43200`` (30 days)

``INGEST_EXPIRY_MINUTES``
~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``2880`` (2 days)

``SPIKE_EXPIRY_MINUTES``
~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``None``

Will use value from ``CONTENT_EXPIRY_MINUTES`` when empty.

``MAX_VALUE_OF_INGEST_SEQUENCE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``9999``

``MAX_VALUE_OF_PUBLISH_SEQUENCE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``9999``

``DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'AAP'``

``DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``6``

``DEFAULT_URGENCY_VALUE_FOR_MANUAL_ARTICLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``3``

``DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``[{'qcode': 'Article', 'name': 'Article (news)'}]``

``RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``False``

``NEWSML_PROVIDER_ID``
~~~~~~~~~~~~~~~~~~~~~~

Default: ``'sourcefabric.org'``

``ORGANIZATION_NAME``
~~~~~~~~~~~~~~~~~~~~~

Default: ``'Australian Associated Press'``

``ORGANIZATION_NAME_ABBREVIATION``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'AAP'``

``NO_TAKES``
~~~~~~~~~~~~

Default: ``False``

Disable creation of takes packages.

``MAX_TRANSMIT_RETRY_ATTEMPT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``10``

Max retries attemps when transmitting an item.

``TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``3``

Delay between retry attempts.

``MAX_TRANSMIT_QUERY_LIMIT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``500``

Max transmit items to be fetched from mongo at once.

``ODBC_PUBLISH``
~~~~~~~~~~~~~~~~

Default: ``None``

Determines if the ODBC publishing mechanism will be used, If enabled then pyodbc must be installed along with it’s dependencies.

Mongo connections
-----------------

There are multiple connections by default, so that it can use different instances for legal archive
and production content.

For each there is ``_DBNAME`` and ``_URI`` setting, if ``_URI`` is set it will be used as is, if not it will
use ``localhost`` as server and ``_DBNAME`` as db.

``MONGO_DBNAME``
~~~~~~~~~~~~~~~~

Default: ``'superdesk'``

``MONGO_URI``
~~~~~~~~~~~~~

Default: ``'mongodb://localhost/superdesk'``

``LEGAL_ARCHIVE_DBNAME``
~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'legal_archive'``

``LEGAL_ARCHIVE_URI``
~~~~~~~~~~~~~~~~~~~~~

Default: ``'mongodb://localhost/legal_archive'``

``ARCHIVED_DBNAME``
~~~~~~~~~~~~~~~~~~~

Default: ``'archived'``

``ARCHIVED_URI``
~~~~~~~~~~~~~~~~

Default: ``mongodb://localhost/archived'``

Elastic settings
----------------

``ELASTICSEARCH_URL``
~~~~~~~~~~~~~~~~~~~~~

Default: ``'http://localhost:9200'``

``ELASTICSEARCH_INDEX``
~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'superdesk'``

Redis settings
--------------

``REDIS_URL``
~~~~~~~~~~~~~

Default: ``'redis://localhost:6379'``

Cache settings
--------------

``CACHE_URL``
~~~~~~~~~~~~~

Default: ``'redis://localhost:6379'``

.. versionadded:: 1.3

Celery settings
---------------

``BROKER_URL``
~~~~~~~~~~~~~~

Default: ``'redis://localhost:6379'``

Monitoring settings
-------------------

``SENTRY_DSN``
~~~~~~~~~~~~~~

Default: ``None``

LDAP settings
-------------

Used for *LDAP* based authentication, if not configured it will use mongodb for credentials.

``LDAP_SERVER``
~~~~~~~~~~~~~~~

Default: ``''``

``LDAP_SERVER_PORT``
~~~~~~~~~~~~~~~~~~~~

Default: ``389``

``LDAP_FQDN``
~~~~~~~~~~~~~

Default: ``''``

``LDAP_BASE_FILTER``
~~~~~~~~~~~~~~~~~~~~

Default: ``''``

``LDAP_USER_FILTER``
~~~~~~~~~~~~~~~~~~~~

Default: ``'(&(objectCategory=user)(objectClass=user)(sAMAccountName={}))'``

``LDAP_USER_ATTRIBUTES``
~~~~~~~~~~~~~~~~~~~~~~~~

Default::

    {
        'givenName': 'first_name',
        'sn': 'last_name',
        'ipPhone': 'phone',
        'mail': 'email',
        'displayName':
        'display_name'
    }

Amazon S3 settings
------------------

``AMAZON_CONTAINER_NAME``
~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``''``

``AMAZON_ACCESS_KEY_ID``
~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``''``

``AMAZON_SECRET_ACCESS_KEY``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``''``

``AMAZON_REGION``
~~~~~~~~~~~~~~~~~

Default: ``'us-east-1'``

``AMAZON_SERVE_DIRECT_LINKS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``False``

``AMAZON_S3_USE_HTTPS``
~~~~~~~~~~~~~~~~~~~~~~~

Default: ``False``

``AMAZON_SERVER``
~~~~~~~~~~~~~~~~~

Default: ``'amazonaws.com'``

``AMAZON_PROXY_SERVER``
~~~~~~~~~~~~~~~~~~~~~~~

Default: ``None``

Security settings
-----------------

``SESSION_EXPIRY_MINUTES``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``240``

The number of minutes since the last update of the Mongo auth object after which it will be deleted.

``RESET_PASSWORD_TOKEN_TIME_TO_LIVE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``1``

The number of days a token is valid, env ``RESET_PASS_TTL``.

``ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``7``

The number of days an activation token is valid, env ``ACTIVATE_TTL``.

Email settings
--------------

``MAIL_SERVER``
~~~~~~~~~~~~~~~

Default: ``'localhost'``

``MAIL_PORT``
~~~~~~~~~~~~~

Default: ``25``

``MAIL_USE_TLS``
~~~~~~~~~~~~~~~~

Default: ``False``

``MAIL_USE_SSL``
~~~~~~~~~~~~~~~~

Default: ``False``

``MAIL_USERNAME``
~~~~~~~~~~~~~~~~~

Default: ``''``

``MAIL_PASSWORD``
~~~~~~~~~~~~~~~~~

Default: ``''``

``MAIL_DEFAULT_SENDER``
~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'superdesk@localhost'``

``ADMINS``
~~~~~~~~~~

Default: ``['']``
