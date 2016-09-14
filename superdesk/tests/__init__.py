# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


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


def get_test_settings():
    test_settings = {}
    test_settings['ELASTICSEARCH_INDEX'] = 'sptest'
    test_settings['MONGO_URI'] = get_mongo_uri('MONGO_URI', 'sptests')
    test_settings['LEGAL_ARCHIVE_DBNAME'] = 'sptests_legal_archive'
    test_settings['LEGAL_ARCHIVE_URI'] = get_mongo_uri('LEGAL_ARCHIVE_URI', 'sptests_legal_archive')
    test_settings['ARCHIVED_DBNAME'] = 'sptests_archived'
    test_settings['ARCHIVED_URI'] = get_mongo_uri('ARCHIVED_URI', 'sptests_archived')
    test_settings['DEBUG'] = True
    test_settings['TESTING'] = True
    test_settings['SUPERDESK_TESTING'] = True
    test_settings['BCRYPT_GENSALT_WORK_FACTOR'] = 4
    test_settings['CELERY_ALWAYS_EAGER'] = 'True'
    test_settings['CONTENT_EXPIRY_MINUTES'] = 99
    test_settings['VERSION'] = '_current_version'
    test_settings['ELASTICSEARCH_BACKUPS_PATH'] = '/tmp/es-backups'

    # limit mongodb connections
    test_settings['MONGO_CONNECT'] = False
    test_settings['ARCHIVED_CONNECT'] = False
    test_settings['LEGAL_ARCHIVE_CONNECT'] = False
    test_settings['MONGO_MAX_POOL_SIZE'] = 1
    test_settings['ARCHIVED_MAX_POOL_SIZE'] = 1
    test_settings['LEGAL_ARCHIVE_MAX_POOL_SIZE'] = 1
    return test_settings


def drop_elastic(app):
    with app.app_context():
        es = app.data.elastic.es
        indexes = [app.config['ELASTICSEARCH_INDEX']] + list(app.config['ELASTICSEARCH_INDEXES'].values())
        for index in indexes:
            es.indices.delete(index, ignore=[404])


def drop_mongo(app):
    with app.app_context():
        drop_mongo_db(app, 'MONGO', 'MONGO_DBNAME')
        drop_mongo_db(app, 'ARCHIVED', 'ARCHIVED_DBNAME')
        drop_mongo_db(app, 'LEGAL_ARCHIVE', 'LEGAL_ARCHIVE_DBNAME')


def drop_mongo_db(app, db_prefix, dbname):
    if app.config.get(dbname):
        db = app.data.mongo.pymongo(prefix=db_prefix).cx
        db.drop_database(app.config[dbname])
        db.close()


def setup_config(config):
    app_abspath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app_config = Config(app_abspath)
    app_config.from_object('superdesk.tests.test_settings')
    app_config['APP_ABSPATH'] = app_abspath

    app_config.update(get_test_settings())
    app_config.update(config or {})

    app_config.update({
        'DEBUG': True,
        'TESTING': True,
    })

    logging.getLogger('superdesk').setLevel(logging.WARNING)
    logging.getLogger('elastic').setLevel(logging.WARNING)  # elastic datalayer
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    return app_config


def clean_dbs(app, force=False):
    clean_es(app, force)
    drop_mongo(app)


def clean_es(app, force=False):
    if not hasattr(clean_es, 'run') or force:
        def run():
            """
            Drop and init elasticsearch indices if backups directory doesn't exist
            """
            drop_elastic(app)
            app.data.init_elastic(app)

        path = app.config['ELASTICSEARCH_BACKUPS_PATH']
        if path and os.path.exists(path):
            run()  # drop and init ones

            backup = ('backups', 'snapshot_1')
            indices = 'sptest_*'

            elastic = app.data.elastic
            elastic.es.snapshot.delete(*backup, ignore=[404])
            elastic.es.snapshot.create(*backup, wait_for_completion=True, body={
                'indices': indices,
                'allow_no_indices': False,
            })

            def run():
                """
                Just restore elasticsearch indices if backups directory exists
                """
                elastic = app.data.elastic
                elastic.es.indices.close('sptest_*', allow_no_indices=False)
                elastic.es.snapshot.restore(*backup, body={
                    'indices': indices,
                    'allow_no_indices': False
                }, wait_for_completion=True)

        clean_es.run = run

    try:
        clean_es.run()
    except socket.timeout as e:
        logging.exception(e)
        # Trying to get less failures by ES timeouts
        count = getattr(clean_es, 'count_calls', 0)
        if count < 3:
            clean_es.count_calls = count + 1
            clean_es(app, force)


def setup(context=None, config=None, app_factory=get_app, reset=False):
    if not hasattr(setup, 'app') or setup.reset or config:
        cfg = setup_config(config)
        setup.app = app_factory(cfg)
        setup.reset = reset
    app = setup.app

    if context:
        context.app = app
        context.client = app.test_client()

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

    endpoint = endpoint if endpoint.startswith('/') else ('/' + endpoint)
    url = current_app.config['URL_PREFIX'] + endpoint
    return url


def setup_db_user(context, user):
    """
    Setup the user for the DB authentication.
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
        auth_response = context.client.post(get_prefixed_url(context.app, '/auth'),
                                            data=auth_data, headers=context.headers)

        auth_data = json.loads(auth_response.get_data())
        token = auth_data.get('token').encode('ascii')
        auth_id = auth_data.get('_id')
        add_to_context(context, token, user, auth_id)


def setup_ad_user(context, user):
    """
    Setup the AD user for the LDAP authentication.
    The method patches the authenticate_and_fetch_profile method of the ADAuth class
    :param context: test context
    :param dict user: user
    """
    ad_user = user or test_user

    '''
    This is necessary as test_user is in Global scope and del doc['password'] removes the key from test_user and
    for the next scenario, auth_data = json.dumps({'username': ad_user['username'], 'password': ad_user['password']})
    will fail as password key is removed by del doc['password']
    '''
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
        auth_response = context.client.post(get_prefixed_url(context.app, '/auth'),
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
        """
        Wrap `setUp` and `tearDown` methods to run
        `setUpForChildren` and `tearDownForChildren`
        """
        # setUp
        def wrapper(self, *args, **kwargs):
            """Combine `setUp` with `setUpForChildren`"""
            self.setUpForChildren()
            return orig_setup(self, *args, **kwargs)
        orig_setup = cls.setUp
        cls.setUp = wrapper

        # tearDown
        def wrapper(self, *args, **kwargs):
            """Combine `tearDown` with `tearDownForChildren`"""
            self.tearDownForChildren()
            return orig_teardown(self, *args, **kwargs)
        orig_teardown = cls.tearDown
        cls.tearDown = wrapper

    def setUpForChildren(self):
        """
        Run this `setUp` stuff for each children
        """
        setup(self)

        self.ctx = self.app.app_context()
        self.ctx.push()

        def clean_ctx():
            if self.ctx:
                self.ctx.pop()
        self.addCleanup(clean_ctx)

    def tearDownForChildren(self):
        """
        Run this `tearDown` stuff for each children
        """

    def get_fixture_path(self, filename):
        rootpath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(rootpath, 'features', 'steps', 'fixtures', filename)
