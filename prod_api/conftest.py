import pytest

from superdesk.tests import get_mongo_uri, setup
from superdesk.factory import get_app as get_sd_app
from superdesk.auth_server.clients import RegisterClient
from prod_api.app import get_app as get_prodapi_api


MONGO_DB = 'prodapi_tests'
ELASTICSEARCH_INDEX = 'prodapi_tests'


@pytest.fixture(scope='function')
def superdesk_app(request):
    """
    Superdesk app.

    :return: superdesk app
    :rtype: superdesk.factory.app.SuperdeskEve
    """

    test_config = {
        'MONGO_URI': get_mongo_uri('MONGO_URI', MONGO_DB),
        'ELASTICSEARCH_INDEX': ELASTICSEARCH_INDEX,
    }
    context = lambda: None
    context.app = None
    context.ctx = None
    context.client = None
    setup(context=context, config=test_config, app_factory=get_sd_app)

    return context.app


@pytest.fixture(scope='function')
def prodapi_app(request):
    """
    Prod api app.

    :return: prod api app
    :rtype: eve.flaskapp.Eve
    """

    test_config = {
        'DEBUG': True,
        'TESTING': True,
        'SUPERDESK_TESTING': True,
        'MONGO_CONNECT': False,
        'MONGO_MAX_POOL_SIZE': 1,
        'MONGO_URI': get_mongo_uri('MONGO_URI', MONGO_DB),
        'ELASTICSEARCH_INDEX': ELASTICSEARCH_INDEX,
        'PRODAPI_URL_PREFIX': 'prodapi',
        'URL_PREFIX': 'prodapi',
    }
    prodapi_app = get_prodapi_api(test_config)

    return prodapi_app


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
def auth_server_registered_client(superdesk_app):
    with superdesk_app.app_context():
        client_data = {
            "name": "soyuz-spacecraft",
            "client_id": "0102030405060708090a0b0c",
            "password": "secret_pwd_123",
            "scope": ["ARCHIVE_READ"]
        }
        RegisterClient().run(**client_data)

    return client_data
