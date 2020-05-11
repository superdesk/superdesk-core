import os
import json
import pytest
from pathlib import Path
from bson import ObjectId
from flask import url_for
from requests.auth import _basic_auth_str

from superdesk.tests import get_mongo_uri, setup, clean_dbs
from superdesk.factory import get_app as get_sd_app
from superdesk.auth_server.clients import RegisterClient
from prod_api.app import get_app as get_prodapi_api


MONGO_DB = 'prodapi_tests'
ELASTICSEARCH_INDEX = MONGO_DB
AUTH_SERVER_SHARED_SECRET = '2kZOf0VI9T70vU9uMlKLyc5GlabxVgl6'


def get_test_prodapi_app(extra_config=None):
    """
    Create and return configured test prod api flask app.
    :param extra_config: extra settings
    :return: eve.flaskapp.Eve
    """
    test_config = {
        'DEBUG': True,
        'TESTING': True,
        'SUPERDESK_TESTING': True,
        'MONGO_CONNECT': False,
        'MONGO_MAX_POOL_SIZE': 1,
        'MONGO_DBNAME': MONGO_DB,
        'MONGO_URI': get_mongo_uri('MONGO_URI', MONGO_DB),
        'ELASTICSEARCH_INDEX': ELASTICSEARCH_INDEX,
        'PRODAPI_URL': 'http://localhost:5500',
        'MEDIA_PREFIX': 'http://localhost:5500/prodapi/v1/assets',
        'PRODAPI_URL_PREFIX': 'prodapi',
        'URL_PREFIX': 'prodapi',
        'AUTH_SERVER_SHARED_SECRET': AUTH_SERVER_SHARED_SECRET
    }
    if extra_config:
        test_config.update(extra_config)
    prodapi_app = get_prodapi_api(test_config)

    # put elastic mapping
    with prodapi_app.app_context():
        prodapi_app.data.elastic.init_index()

    return prodapi_app


def get_test_superdesk_app(extra_config=None):
    """
    Create and return configured test superdesk flask app.
    :param extra_config: extra settings
    :return: eve.flaskapp.Eve
    """
    test_config = {
        'MONGO_DBNAME': MONGO_DB,
        'MONGO_URI': get_mongo_uri('MONGO_URI', MONGO_DB),
        'ELASTICSEARCH_INDEX': ELASTICSEARCH_INDEX,
        'AUTH_SERVER_SHARED_SECRET': AUTH_SERVER_SHARED_SECRET,
    }
    if extra_config:
        test_config.update(extra_config)

    def context():
        pass

    context.app = None
    context.ctx = None
    context.client = None
    setup(context=context, config=test_config, app_factory=get_sd_app)

    return context.app


def teardown_app(app):
    """
    Drop test db and test app
    """
    clean_dbs(app)
    del app


@pytest.fixture(scope='function')
def superdesk_app(request):
    """
    Superdesk app.

    :return: superdesk app
    :rtype: superdesk.factory.app.SuperdeskEve
    """

    extra_config = getattr(request, 'param', {})
    app = get_test_superdesk_app(extra_config)

    def test_app_teardown():
        """
        Drop test db and test app
        """
        teardown_app(app)

    request.addfinalizer(test_app_teardown)

    return app


@pytest.fixture(scope='function')
def prodapi_app(request):
    """
    Prod api app.

    :return: prod api app
    :rtype: eve.flaskapp.Eve
    """

    extra_config = getattr(request, 'param', {})
    app = get_test_prodapi_app(extra_config)

    def test_app_teardown():
        """
        Drop test db and test app
        """
        teardown_app(app)

    request.addfinalizer(test_app_teardown)

    return app


@pytest.fixture(scope='module')
def prodapi_app_with_data(request):
    """
    Prod api app with prefilled collections and with disabled auth.
    ATTENTION: This is a resource-heavy fixture and it's designed to use with "module" scope.
    It's better to use it in readonly tests and not modify data of fixtured app.

    :return: prod api app
    :rtype: eve.flaskapp.Eve
    """

    extra_config = getattr(request, 'param', {})
    extra_config['PRODAPI_AUTH_ENABLED'] = False
    app = get_test_prodapi_app(extra_config)

    # fill with data
    with app.app_context():
        p = Path(os.path.join(os.path.dirname(__file__), 'tests/fixtures'))
        for fixture_file in [x for x in p.iterdir() if x.is_file()]:
            with fixture_file.open() as f:
                app.data.insert(
                    resource=fixture_file.stem,
                    docs=json.loads(f.read())
                )

    def test_app_teardown():
        """
        Drop test db and test app
        """
        teardown_app(app)

    request.addfinalizer(test_app_teardown)

    return app


@pytest.fixture(scope='module')
def prodapi_app_with_data_client(prodapi_app_with_data):
    """Test client for prod api with filled data"""

    client = prodapi_app_with_data.test_client()

    with prodapi_app_with_data.app_context():
        yield client


@pytest.fixture(scope='function')
def prodapi_client(prodapi_app):
    """Test client for prod api"""

    client = prodapi_app.test_client()

    with prodapi_app.app_context():
        yield client


@pytest.fixture(scope='function')
def superdesk_client(superdesk_app):
    """Test client for superdesk"""

    client = superdesk_app.test_client()

    with superdesk_app.app_context():
        yield client


@pytest.fixture(scope='function')
def auth_server_registered_clients(request, superdesk_app):
    """
    Registers clients for auth server.
    :return: dict with clients
    """
    clients_data = []

    with superdesk_app.app_context():
        for param in request.param:
            # register clients
            clients_data.append({
                "name": str(ObjectId()),  # just a random string
                "client_id": str(ObjectId()),
                "password": str(ObjectId()),  # just a random string
                "scope": param
            })
            RegisterClient().run(**clients_data[-1])

    return clients_data


@pytest.fixture(scope='function')
def issued_tokens(request, superdesk_app, superdesk_client):
    tokens = []
    clients_data = []

    # register clients
    with superdesk_app.app_context():
        for param in request.param:
            clients_data.append({
                "name": str(ObjectId()),  # just a random string
                "client_id": str(ObjectId()),
                "password": str(ObjectId()),  # just a random string
                "scope": param
            })
            RegisterClient().run(**clients_data[-1])

    # retrieve tokens
    with superdesk_app.test_request_context():
        for client_data in clients_data:
            resp = superdesk_client.post(
                url_for('auth_server.issue_token'),
                data={
                    'grant_type': 'client_credentials'
                },
                headers={
                    'Authorization': _basic_auth_str(client_data['client_id'], client_data['password'])
                }
            )
            tokens.append(json.loads(resp.data.decode('utf-8')))

    teardown_app(superdesk_app)
    del superdesk_client

    return tokens
