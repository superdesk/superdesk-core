.. _settings:

.. module:: superdesk.default_settings

=============
Configuration
=============

We use ``flask.app.config``, so to use it do::

    from flask import current_app as app

    print(app.config['SERVER_DOMAIN'])

Configuration is combination of default settings module and settings module
in `application repo <https://github.com/superdesk/superdesk/blob/master/server/settings.py>`_.

.. _settings.default:

Default settings
----------------

``APPLICATION_NAME``
^^^^^^^^^^^^^^^^^^^^

Default: ``'Superdesk'``

.. _settings.default.client_url:

``CLIENT_URL``
^^^^^^^^^^^^^^

Default: ``'http://localhost:9000'``

``DEFAULT_TIMEZONE``
^^^^^^^^^^^^^^^^^^^^

Default: ``None``

Superdesk will try to guess the value from system if not set.

``FTP_TIMEOUT``
^^^^^^^^^^^^^^^

Default: ``300``

This is used for all ftp operations. Increase if you get ftp timeout errors.

.. _settings.installed_apps:

``INSTALLED_APPS``
^^^^^^^^^^^^^^^^^^

Default: ``[]``

You can install additional modules by adding their names here.

``CONTENT_EXPIRY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionchanged:: 1.5
    Change default value to ``0``.

Default: ``0``

By default content will not expire.

``ARCHIVED_EXPIRY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 1.34

Default: ``0``

``PUBLISHED_CONTENT_EXPIRY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``0``

It applies only to published content if the value is greater than ``0`` and it overrides the desk/stage content
expiry settings. If ``PUBLISHED_CONTENT_EXPIRY_MINUTES`` is set to ``0`` then the content is expired based on
the content expiry settings for that desk/stage.

``INGEST_EXPIRY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``2880`` (2 days)

``SPIKE_EXPIRY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``None``

Will use value from ``CONTENT_EXPIRY_MINUTES`` when empty.

``MAX_VALUE_OF_INGEST_SEQUENCE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``9999``

``MAX_VALUE_OF_PUBLISH_SEQUENCE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``9999``

``DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'Superdesk'``

.. versionchanged:: 1.8
    Change default value to ``'Superdesk'``.

``DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``6``

``DEFAULT_URGENCY_VALUE_FOR_MANUAL_ARTICLES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``3``

``DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``[{'qcode': 'Article', 'name': 'Article (news)'}]``

``RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``False``

``NEWSML_PROVIDER_ID``
^^^^^^^^^^^^^^^^^^^^^^

Default: ``'sourcefabric.org'``

``ORGANIZATION_NAME``
^^^^^^^^^^^^^^^^^^^^^

Default: ``'Your organisation'``

.. versionchanged:: 1.8
    Change default value to ``'Your organisation'``.

``ORGANIZATION_NAME_ABBREVIATION``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'Short name for your organisation'``

.. versionchanged:: 1.8
    Change default value to ``'Short name for your organisation'``.

``MAX_TRANSMIT_RETRY_ATTEMPT``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``10``

Max retries attemps when transmitting an item.

``TRANSMIT_RETRY_ATTEMPT_DELAY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``3``

Delay between retry attempts.

``MAX_TRANSMIT_QUERY_LIMIT``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``500``

Max transmit items to be fetched from mongo at once.

``ODBC_PUBLISH``
^^^^^^^^^^^^^^^^

Default: ``None``

Determines if the ODBC publishing mechanism will be used. If enabled then pyodbc must be
installed along with its dependencies.

.. _settings.mongo:

Mongo connections
-----------------

There are multiple connections by default, so that it can use different instances for legal archive
and production content.

For each there is ``_DBNAME`` and ``_URI`` setting, if ``_URI`` is set it will be used as is, if not it will
use ``localhost`` as server and ``_DBNAME`` as db.

``MONGO_DBNAME``
^^^^^^^^^^^^^^^^

Default: ``'superdesk'``

``MONGO_URI``
^^^^^^^^^^^^^

Default: ``'mongodb://localhost/superdesk'``

``LEGAL_ARCHIVE_DBNAME``
^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'legal_archive'``

``LEGAL_ARCHIVE_URI``
^^^^^^^^^^^^^^^^^^^^^

Default: ``'mongodb://localhost/legal_archive'``

``ARCHIVED_DBNAME``
^^^^^^^^^^^^^^^^^^^

Default: ``'archived'``

``ARCHIVED_URI``
^^^^^^^^^^^^^^^^

Default: ``mongodb://localhost/archived'``

.. _settings.elastic:

Elastic settings
----------------

``ELASTICSEARCH_URL``
^^^^^^^^^^^^^^^^^^^^^

Default: ``'http://localhost:9200'``

``ELASTICSEARCH_INDEX``
^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'superdesk'``

.. _settings.redis:

Redis settings
--------------

``REDIS_URL``
^^^^^^^^^^^^^

Default: ``'redis://localhost:6379'``

.. _settings.cache:

Cache settings
--------------

``CACHE_URL``
^^^^^^^^^^^^^

Default: ``'redis://localhost:6379'``

.. versionadded:: 1.3

.. _settings.celery:

Celery settings
---------------

``BROKER_URL``
^^^^^^^^^^^^^^

Default: ``'redis://localhost:6379'``

``CELERY_WORKER_CONCURRENCY``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``None``

If not set it will be the number of CPUs available.

``HIGH_PRIORITY_QUEUE_ENABLED``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 1.31

Default: ``False``

When enabled you can toggle subscriber priority and those with high priority will use
dedicated celery queue for transmissions.
This should be only enabled when you have dedicated worker running::

    $ celery -A worker worker -Q publish_priority

.. _settings.monitoring:

Monitoring settings
-------------------

``SENTRY_DSN``
^^^^^^^^^^^^^^

Default: ``None``

.. _settings.ldap:

LDAP settings
-------------

Used for *LDAP* based authentication, if not configured it will use mongodb for credentials.

``LDAP_SERVER``
^^^^^^^^^^^^^^^

Default: ``''``

``LDAP_SERVER_PORT``
^^^^^^^^^^^^^^^^^^^^

Default: ``389``

``LDAP_FQDN``
^^^^^^^^^^^^^

Default: ``''``

``LDAP_BASE_FILTER``
^^^^^^^^^^^^^^^^^^^^

Default: ``''``

``LDAP_USER_FILTER``
^^^^^^^^^^^^^^^^^^^^

Default: ``'(&(objectCategory=user)(objectClass=user)(sAMAccountName={}))'``

``LDAP_USER_ATTRIBUTES``
^^^^^^^^^^^^^^^^^^^^^^^^

Default::

    {
        'givenName': 'first_name',
        'sn': 'last_name',
        'ipPhone': 'phone',
        'mail': 'email',
        'displayName': 'display_name'
    }

.. _settings.media:

Media settings
--------------

``MEDIA_PREFIX``
^^^^^^^^^^^^^^^^

Default: ``''``

Uses for generation of media url ``(<media_prefix>/<media_id>)``::

    # if it's empty (default value) uses something like
    'http://<host>/api/upload-raw'

    # serve directly from AMAZON S3
    'https://<bucket>.s3-<region>.amazonaws.com/<subfolder>'

    # save relative urls to database
    '/media-via-nginx'
    # or using api view
    '/api/upload-raw'

.. _settings.amazons3:

Amazon S3 settings
------------------

``AMAZON_ACCESS_KEY_ID``
^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``''``

``AMAZON_SECRET_ACCESS_KEY``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``''``

``AMAZON_REGION``
^^^^^^^^^^^^^^^^^

Default: ``'us-east-1'``

``AMAZON_CONTAINER_NAME``
^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``''``

``AMAZON_S3_SUBFOLDER``
^^^^^^^^^^^^^^^^^^^^^^^

Default: ``''``

``AMAZON_OBJECT_ACL``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``''``

.. _settings.security:

Security settings
-----------------

``SESSION_EXPIRY_MINUTES``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``240``

The number of minutes since the last update of the Mongo auth object after which it will be deleted.

``RESET_PASSWORD_TOKEN_TIME_TO_LIVE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``1``

The number of days a token is valid, env ``RESET_PASS_TTL``.

``ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``7``

The number of days an activation token is valid, env ``ACTIVATE_TTL``.

.. _settings.secret_key:

``SECRET_KEY``
^^^^^^^^^^^^^^

.. versionadded:: 1.5

Default: ``''``

This value should be set to a unique, unpredictable value. It is used for auth token signing.

.. _settings.email:

Email settings
--------------

``MAIL_SERVER``
^^^^^^^^^^^^^^^

Default: ``'localhost'``

``MAIL_PORT``
^^^^^^^^^^^^^

Default: ``25``

``MAIL_USE_TLS``
^^^^^^^^^^^^^^^^

Default: ``False``

``MAIL_USE_SSL``
^^^^^^^^^^^^^^^^

Default: ``False``

``MAIL_USERNAME``
^^^^^^^^^^^^^^^^^

Default: ``''``

``MAIL_PASSWORD``
^^^^^^^^^^^^^^^^^

Default: ``''``

``MAIL_DEFAULT_SENDER``
^^^^^^^^^^^^^^^^^^^^^^^

Default: ``'superdesk@localhost'``

``ADMINS``
^^^^^^^^^^

Default: ``['']``

.. _settings.content_api:

Content API Settings
--------------------

.. versionadded:: 1.5

``CONTENTAPI_URL``

Default: ``localhost:5400``

Content API URL. Set this when running api behind a proxy.

``CONTENT_API_ENABLED``
^^^^^^^^^^^^^^^^^^^^^^^

Default: ``True``

Set to false to disable publishing to Content API.

``CONTENT_API_EXPIRY_DAYS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``0``

Define after how many days items expire in content api. When set to ``0`` no items will be removed.

``CONTENTAPI_MONGO_DBNAME``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``contentapi``

``CONTENTAPI_MONGO_URI``
^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``mongodb://localhost/contentapi``

``CONTENTAPI_ELASTICSEARCH_URL``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``http://localhost:9200``

``CONTENTAPI_ELASTICSEARCH_INDEX``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``contentapi``

.. _settings.google_oauth:

Google OAuth Settings
---------------------

.. versionadded:: 1.8

``GOOGLE_CLIENT_ID``
^^^^^^^^^^^^^^^^^^^^

Default: ``''``

``GOOGLE_CLIENT_SECRET``
^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``''``

SAML Auth Settings
------------------

.. versionadded:: 1.9

.. _settings.saml_path:

``SAML_PATH``
^^^^^^^^^^^^^

Default: ``None``

``SAML_LABEL``
^^^^^^^^^^^^^^

Default: ``'Single Sign On'``

Label on auth button for SAML.

OpenID Connect Auth Settings
----------------------------

.. versionadded:: 2.1

.. _settings.oidc_oauth:

``OIDC_ENABLED``
^^^^^^^^^^^^^^^^

Default: ``False``

``OIDC_ISSUER_URL``
^^^^^^^^^^^^^^^^^^^

Default: ``http://localhost:8080/auth/realms/SUPERDESK_REALM``

Issuer URL address

``OIDC_SERVER_CLIENT``
^^^^^^^^^^^^^^^^^^^^^^

Keycloak client name with `access type <https://www.keycloak.org/docs/latest/server_admin/#_access-type>`_ is confidential

``OIDC_SERVER_CLIENT_SECRET``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Keycloak server client secret

``OIDC_WEB_CLIENT``
^^^^^^^^^^^^^^^^^^^

Keycloak client name with access type is public

``OIDC_BROWSER_REDIRECT_URL``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: :ref:`settings.default.client_url`

Redirect URL for successful authentication with Keycloak

Schema and Editor
-----------------

.. versionadded:: 1.9

Allows updating schema and editor settings for item types ``text``, ``picture`` and ``composite``.


``SCHEMA``
^^^^^^^^^^

Default: ``{}``

Example::

    SCHEMA = {
        'composite': {
            'headline': {'type': 'text', 'required': True, 'maxlength': 200},
            ...
        }
    }


``EDITOR``
^^^^^^^^^^

Default: ``{}``

Example::

    EDITOR = {
        'composite': {
            'headline': {'order': 1, formatOptions: ['bold']},
            ...
        }
    }


``OVERRIDE_EDNOTE_FOR_CORRECTIONS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``True``

Set to False to disable editor note overriding on correction.

``OVERRIDE_EDNOTE_TEMPLATE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``None``

Template to use to override editor note (ignored if ``OVERRIDE_EDNOTE_FOR_CORRECTIONS`` is ``False``).
If not set, default template will be used.
In your template, you can use ``{date}`` to insert current date or ``{slugline}`` for slugline.

Example::

    OVERRIDE_EDNOTE_FOR_CORRECTIONS = True
    OVERRIDE_EDNOTE_TEMPLATE = 'Story "{slugline}" corrected on {date}'

``ALLOW_UPDATING_SCHEDULED_ITEMS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``None``

Set to True to allow updating the schedule items.

``GEONAMES_USERNAME``
^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 1.20

Default: ``None``

When configured it will enable ``/places_autocomplete`` service and client
will use it for place field searching.

Other
-----

.. autodata:: KEYWORDS_ADD_MISSING_ON_PUBLISH

.. autodata:: WORKFLOW_ALLOW_MULTIPLE_UPDATES

.. autodata:: ARCHIVE_AUTOCOMPLETE
.. autodata:: ARCHIVE_AUTOCOMPLETE_DAYS
.. autodata:: ARCHIVE_AUTOCOMPLETE_HOURS

.. autodata:: LINKS_MAX_HOURS

.. _settings.extending:

Extend Superdesk
-----------------

Additional settings which are allowed to change some Superdesk defaults

``SCHEMA_UPDATE``

Default: ``None``

Allows to update a default schema.

Example::

    SCHEMA_UPDATE = {
        'archive': {
            'extra': {
                'type': 'dict',
                'schema': {},
                'mapping': {
                    'type': 'object',
                    'enabled': True
                },
                'allow_unknown': True,
            }
        }
    }

Video server settings
---------------------

``VIDEO_SERVER_URL``
^^^^^^^^^^^^^^^^^^^^^^^

Default: ``http://localhost:5050``

Video server API url.

``VIDEO_SERVER_ENABLED``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``False``

Enable video server.
