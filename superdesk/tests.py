# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
import pymongo
import unittest
import elasticsearch
import logging

from base64 import b64encode
from flask import json, Config
from superdesk.notification_mock import setup_notification_mock, teardown_notification_mock
from superdesk import get_resource_service
from superdesk.factory import get_app
from eve_elastic import get_es, get_indices

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
    return test_settings


def drop_elastic(app):
    with app.app_context():
        try:
            es = get_es(app.config['ELASTICSEARCH_URL'])
            get_indices(es).delete(app.config['ELASTICSEARCH_INDEX'])
        except elasticsearch.exceptions.NotFoundError:
            pass


def drop_mongo(app):
    with app.app_context():
        drop_mongo_db(app, 'MONGO', 'MONGO_DBNAME')
        drop_mongo_db(app, 'LEGAL_ARCHIVE', 'LEGAL_ARCHIVE_DBNAME')
        drop_mongo_db(app, 'ARCHIVED', 'ARCHIVED_DBNAME')


def drop_mongo_db(app, db_prefix, dbname):
    try:
        if app.config.get(dbname):
            app.data.mongo.pymongo(prefix=db_prefix).cx.drop_database(app.config[dbname])
    except pymongo.errors.ConnectionFailure:
        raise ValueError('Invalid mongo config or server is down (uri=%s db=%s)' %
                         (db_prefix, app.config[dbname]))
    except AttributeError:
        pass


def setup(context=None, config=None, app_factory=get_app):

    app_abspath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app_config = Config(app_abspath)
    app_config.from_object('test_settings')
    app_config['APP_ABSPATH'] = app_abspath

    app_config.update(get_test_settings())
    app_config.update(config or {})

    app = app_factory(app_config)
    logger = logging.getLogger('superdesk')
    logger.setLevel(logging.ERROR)
    logger = logging.getLogger('elasticsearch')
    logger.setLevel(logging.ERROR)
    logger = logging.getLogger('urllib3')
    logger.setLevel(logging.ERROR)
    drop_elastic(app)
    drop_mongo(app)

    # create index again after dropping it
    app.data.elastic.init_app(app)

    if context:
        context.app = app
        context.client = app.test_client()


def setup_auth_user(context, user=None):
    setup_db_user(context, user)


def add_to_context(context, token, user):
    context.headers.append(('Authorization', b'basic ' + b64encode(token + b':')))
    context.user = user
    set_placeholder(context, 'CONTEXT_USER_ID', str(user.get('_id')))


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

        token = json.loads(auth_response.get_data()).get('token').encode('ascii')
        add_to_context(context, token, user)


def setup_notification(context):
    setup_notification_mock(context)


def teardown_notification(context):
    teardown_notification_mock(context)


class TestCase(unittest.TestCase):

    def setUp(self):
        setup(self, app_factory=get_app)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        if hasattr(self, 'ctx'):
            self.ctx.pop()

    def get_fixture_path(self, filename):
        rootpath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(rootpath, 'features', 'steps', 'fixtures', filename)
