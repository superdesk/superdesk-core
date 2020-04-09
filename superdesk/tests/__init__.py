# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import functools
import logging
import os
import socket
import unittest
from base64 import b64encode
from unittest.mock import patch

from flask import json, Config

from apps.ldap import ADAuth
from superdesk import get_resource_service
from superdesk.factory import get_app

logger = logging.getLogger(__name__)
test_user = {
    'username': 'test_user',
    'password': 'test_password',
    'is_active': True,
    'is_enabled': True,
    'needs_activation': False,
    'sign_off': 'abc',
    'email': 'behave_test@sourcefabric.org',
    'preferences': {
        'email:notification': {
            'label': 'Send notifications via email',
            'type': 'bool',
            'default': True,
            'category': 'notifications',
            'enabled': True}
    }
}


def get_mongo_uri(key, dbname):
    """Read mongo uri from env variable and replace dbname.

    :param key: env variable name
    :param dbname: mongo db name to use
    """
    env_uri = os.environ.get(key, 'mongodb://localhost/test')
    env_host = env_uri.rsplit('/', 1)[0]
    return '/'.join([env_host, dbname])


def update_config(conf):
    conf['ELASTICSEARCH_INDEX'] = 'sptest'
    conf['MONGO_URI'] = get_mongo_uri('MONGO_URI', 'sptests')
    conf['LEGAL_ARCHIVE_DBNAME'] = 'sptests_legal_archive'
    conf['LEGAL_ARCHIVE_URI'] = get_mongo_uri('LEGAL_ARCHIVE_URI', 'sptests_legal_archive')
    conf['ARCHIVED_DBNAME'] = 'sptests_archived'
    conf['ARCHIVED_URI'] = get_mongo_uri('ARCHIVED_URI', 'sptests_archived')
    conf['CONTENTAPI_URL'] = 'http://localhost:5400'
    conf['CONTENTAPI_MONGO_DBNAME'] = 'sptests_contentapi'
    conf['CONTENTAPI_MONGO_URI'] = get_mongo_uri('CONTENTAPI_MONGO_URI', 'sptests_contentapi')
    conf['CONTENTAPI_ELASTICSEARCH_INDEX'] = 'sptest_contentapi'

    conf['DEBUG'] = True
    conf['TESTING'] = True
    conf['SUPERDESK_TESTING'] = True
    conf['BCRYPT_GENSALT_WORK_FACTOR'] = 4
    conf['CELERY_TASK_ALWAYS_EAGER'] = 'True'
    conf['CELERY_BEAT_SCHEDULE_FILENAME'] = './testschedule.db'
    conf['CELERY_BEAT_SCHEDULE'] = {}
    conf['CONTENT_EXPIRY_MINUTES'] = 99
    conf['VERSION'] = '_current_version'
    conf['SECRET_KEY'] = 'test-secret'
    conf['JSON_SORT_KEYS'] = True
    conf['ELASTICSEARCH_INDEXES'] = {
        'archived': 'sptest_archived',
        'archive': 'sptest_archive',
        'ingest': 'sptest_ingest',
    }

    # (behave|nose)tests depends from these settings
    conf['DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES'] = 'AAP'
    conf['MACROS_MODULE'] = 'superdesk.macros'
    conf['DEFAULT_TIMEZONE'] = 'Europe/Prague'
    conf['LEGAL_ARCHIVE'] = True

    # limit mongodb connections
    conf['MONGO_CONNECT'] = False
    conf['ARCHIVED_CONNECT'] = False
    conf['LEGAL_ARCHIVE_CONNECT'] = False
    conf['MONGO_MAX_POOL_SIZE'] = 1
    conf['ARCHIVED_MAX_POOL_SIZE'] = 1
    conf['LEGAL_ARCHIVE_MAX_POOL_SIZE'] = 1

    # misc
    conf['GEONAMES_USERNAME'] = 'superdesk_dev'
    conf['PUBLISH_ASSOCIATED_ITEMS'] = True

    # auth server
    conf['AUTH_SERVER_SHARED_SECRET'] = 'some secret'
    return conf


def drop_elastic(app):
    with app.app_context():
        es = app.data.elastic.es
        indexes = [app.config['ELASTICSEARCH_INDEX']] + list(app.config['ELASTICSEARCH_INDEXES'].values())
        for index in indexes:
            es.indices.delete(index, ignore=[404])


def foreach_mongo(fn):
    """
    Run the same actions on all mongo databases

    This decorator adds two additional parameters to called function
    `dbconn` and `dbname` for using proper connection and database name
    """
    @functools.wraps(fn)
    def inner(app, *a, **kw):
        pairs = (
            ('MONGO', 'MONGO_DBNAME'),
            ('ARCHIVED', 'ARCHIVED_DBNAME'),
            ('LEGAL_ARCHIVE', 'LEGAL_ARCHIVE_DBNAME'),
            ('CONTENTAPI_MONGO', 'CONTENTAPI_MONGO_DBNAME')
        )
        with app.app_context():
            for prefix, name in pairs:
                if not app.config.get(name):
                    continue
                kw['dbname'] = app.config[name]
                kw['dbconn'] = app.data.mongo.pymongo(prefix=prefix).cx
                fn(app, *a, **kw)
    return inner


@foreach_mongo
def drop_mongo(app, dbconn, dbname):
    dbconn.drop_database(dbname)
    dbconn.close()


def setup_config(config):
    app_abspath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app_config = Config(app_abspath)
    app_config.from_object('superdesk.default_settings')

    update_config(app_config)
    app_config.update(config or {}, **{
        'APP_ABSPATH': app_abspath,
        'DEBUG': True,
        'TESTING': True,
    })

    logging.getLogger('apps').setLevel(logging.WARNING)
    logging.getLogger('elastic').setLevel(logging.WARNING)  # elastic datalayer
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.WARNING)
    logging.getLogger('superdesk').setLevel(logging.ERROR)
    logging.getLogger('elasticsearch').setLevel(logging.ERROR)
    logging.getLogger('superdesk.errors').setLevel(logging.CRITICAL)
    return app_config


def clean_dbs(app, force=False):
    clean_es(app, force)
    drop_mongo(app)


def retry(exc, count=1):
    def wrapper(fn):
        num = 0

        @functools.wraps(fn)
        def inner(*a, **kw):
            global num

            try:
                return fn(*a, **kw)
            except exc as e:
                logging.exception(e)
                if num < count:
                    num += 1
                    return inner(*a, **kw)
        return inner
    return wrapper


def _clean_es(app):
    indices = '%s*' % app.config['ELASTICSEARCH_INDEX']
    es = app.data.elastic.es
    es.indices.delete(indices, ignore=[404])
    with app.app_context():
        app.data.init_elastic(app)


@retry(socket.timeout, 2)
def clean_es(app, force=False):
    use_snapshot(app, 'clean', [snapshot_es], force)(_clean_es)(app)


def snapshot(fn):
    """
    Call create or restore snapshot function
    """
    @functools.wraps(fn)
    def inner(app, name, action, **kw):
        assert action in ['create', 'restore']
        create, restore = fn(app, name, **kw)
        {'create': create, 'restore': restore}[action]()
    return inner


@snapshot
def snapshot_es(app, name):
    indices = '%s*' % app.config['ELASTICSEARCH_INDEX']
    backup = ('backups', '%s%s' % (indices[:-1], name))
    es = app.data.elastic.es

    def create():
        es.snapshot.delete(*backup, ignore=[404])
        es.indices.open(indices, expand_wildcards='closed', ignore=[404])
        es.snapshot.create(*backup, wait_for_completion=True, body={
            'indices': indices,
            'allow_no_indices': False,
        })

    def restore():
        es.indices.close(indices, expand_wildcards='open', ignore=[404])
        es.snapshot.restore(*backup, body={
            'indices': indices,
            'allow_no_indices': False
        }, wait_for_completion=True)
    return create, restore


@foreach_mongo
@snapshot
def snapshot_mongo(app, name, dbconn, dbname):
    snapshot = '%s_%s' % (dbname, name)

    def create():
        dbconn.drop_database(snapshot)
        dbconn.admin.command('copydb', fromdb=dbname, todb=snapshot)

    def restore():
        dbconn.drop_database(dbname)
        dbconn.admin.command('copydb', fromdb=snapshot, todb=dbname)
    return create, restore


def use_snapshot(app, name, funcs=(snapshot_es, snapshot_mongo), force=False):
    def snapshot(action):
        for f in funcs:
            f(app, name, action=action)

    def wrapper(fn):
        path = app.config.get('ELASTICSEARCH_BACKUPS_PATH')
        enabled = path and os.path.exists(path)

        @functools.wraps(fn)
        def inner(*a, **kw):
            if not enabled or force:
                logger.debug(
                    'Don\'t use snapshot for %s; enabled=%s; force=%s',
                    fn, enabled, force
                )
                use_snapshot.cache.pop(fn, None)
                return fn(*a, **kw)

            if fn in use_snapshot.cache:
                snapshot('restore')
                logger.debug('Restore snapshot for %s', fn)
            else:
                use_snapshot.cache[fn] = fn(*a, **kw)
                snapshot('create')
                logger.debug('Create snapshot for %s', fn)
            return use_snapshot.cache[fn]
        return inner
    return wrapper


use_snapshot.cache = {}


def setup(context=None, config=None, app_factory=get_app, reset=False):
    if not hasattr(setup, 'app') or setup.reset or config:
        cfg = setup_config(config)
        setup.app = app_factory(cfg)
        setup.reset = reset
    app = setup.app

    if context:
        context.app = app
        context.client = app.test_client()
        if not hasattr(context, 'BEHAVE'):
            app.test_request_context().push()

    clean_dbs(app, force=bool(config))


def setup_auth_user(context, user=None):
    setup_db_user(context, user)


def add_to_context(context, token, user, auth_id=None):
    context.headers.append(('Authorization', b'basic ' + b64encode(token + b':')))
    if getattr(context, 'user', None):
        context.previous_user = context.user
    context.user = user
    set_placeholder(context, 'CONTEXT_USER_ID', str(user.get('_id')))
    set_placeholder(context, 'AUTH_ID', str(auth_id))


def set_placeholder(context, name, value):
    old_p = getattr(context, 'placeholders', None)
    if not old_p:
        context.placeholders = dict()
    context.placeholders[name] = value


def get_prefixed_url(current_app, endpoint):
    if endpoint.startswith('http://'):
        return endpoint

    endpoint = endpoint.lstrip('/')
    url_prefix = current_app.config['URL_PREFIX'] + '/'
    if endpoint.startswith(url_prefix):
        return endpoint
    return url_prefix + endpoint


def setup_db_user(context, user):
    """Setup the user for the DB authentication.

    :param context: test context
    :param dict user: user
    """
    user = user or test_user
    with context.app.test_request_context(context.app.config['URL_PREFIX']):
        original_password = user['password']

        user.setdefault('user_type', 'administrator')

        if not get_resource_service('users').find_one(username=user['username'], req=None):
            get_resource_service('users').post([user])

        user['password'] = original_password
        auth_data = json.dumps({'username': user['username'], 'password': user['password']})
        auth_response = context.client.post(get_prefixed_url(context.app, '/auth_db'),
                                            data=auth_data, headers=context.headers)

        auth_data = json.loads(auth_response.get_data())
        token = auth_data.get('token').encode('ascii')
        auth_id = auth_data.get('_id')
        add_to_context(context, token, user, auth_id)


def setup_ad_user(context, user):
    """Setup the AD user for the LDAP authentication.

    The method patches the authenticate_and_fetch_profile method of the ADAuth class

    :param context: test context
    :param dict user: user
    """
    ad_user = user or test_user

    # This is necessary as test_user is in Global scope and del doc['password']
    # removes the key from test_user and for the next scenario,
    # auth_data = json.dumps({'username': ad_user['username'], 'password': ad_user['password']})
    # will fail as password key is removed by del doc['password']
    ad_user = ad_user.copy()
    ad_user['email'] = 'mock@mail.com.au'

    ad_user.setdefault('user_type', 'administrator')

    # ad profile to be return from the patch object
    ad_profile = {
        'email': ad_user['email'],
        'username': ad_user['username'],
        # so that test run under the administrator context.
        'user_type': ad_user.get('user_type'),
        'sign_off': ad_user.get('sign_off', 'abc'),
        'preferences': {
            'email:notification': {
                'label': 'Send notifications via email',
                'type': 'bool',
                'default': True,
                'category': 'notifications',
                'enabled': True}
        }
    }

    with patch.object(ADAuth, 'authenticate_and_fetch_profile', return_value=ad_profile):
        auth_data = json.dumps({'username': ad_user['username'], 'password': ad_user['password']})
        auth_response = context.client.post(get_prefixed_url(context.app, '/auth_db'),
                                            data=auth_data, headers=context.headers)
        auth_response_as_json = json.loads(auth_response.get_data())
        token = auth_response_as_json.get('token').encode('ascii')
        ad_user['_id'] = auth_response_as_json['user']

        add_to_context(context, token, ad_user)


class NotificationMock:
    def __init__(self):
        self.messages = []
        self.client = None
        self.open = True

    def send(self, message):
        self.messages.append(message)

    def reset(self):
        self.messages = []


def setup_notification(context):
    mock = NotificationMock()
    if context.app.notification_client:
        mock.client = context.app.notification_client
    context.app.notification_client = mock


def teardown_notification(context):
    context.app.notification_client = context.app.notification_client.client


class TestCase(unittest.TestCase):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

        self.app = None
        self.client = None
        self.ctx = None

    @classmethod
    def setUpClass(cls):
        """Wrap `setUp` and `tearDown` methods to run `setUpForChildren` and `tearDownForChildren`."""
        # setUp
        def wrapper(self, *args, **kwargs):
            """Combine `setUp` with `setUpForChildren`."""
            self.setUpForChildren()
            return orig_setup(self, *args, **kwargs)
        orig_setup = cls.setUp
        cls.setUp = wrapper

        # tearDown
        def wrapper(self, *args, **kwargs):
            """Combine `tearDown` with `tearDownForChildren`."""
            self.tearDownForChildren()
            return orig_teardown(self, *args, **kwargs)
        orig_teardown = cls.tearDown
        cls.tearDown = wrapper

    def setUpForChildren(self):
        """Run this `setUp` stuff for each children."""
        setup(self)

        self.ctx = self.app.app_context()
        self.ctx.push()

        def clean_ctx():
            if self.ctx:
                self.ctx.pop()
        self.addCleanup(clean_ctx)

    def tearDownForChildren(self):
        """Run this `tearDown` stuff for each children."""

    def get_fixture_path(self, filename):
        rootpath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(rootpath, 'features', 'steps', 'fixtures', filename)
