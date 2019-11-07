import pytest
from bson import ObjectId

from superdesk.tests import get_mongo_uri, setup
from superdesk.factory import get_app as get_sd_app
from superdesk.auth_server.clients import RegisterClient
from prod_api.app import get_app as get_prodapi_api


MONGO_DB = 'prodapi_tests'
ELASTICSEARCH_INDEX = 'prodapi_tests'
AUTH_SERVER_SHARED_SECRET = '2kZOf0VI9T70vU9uMlKLyc5GlabxVgl6'


def get_test_prodapi_app():
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
        'AUTH_SERVER_SHARED_SECRET': AUTH_SERVER_SHARED_SECRET
    }
    prodapi_app = get_prodapi_api(test_config)

    return prodapi_app


def get_test_superdesk_app():
    test_config = {
        'MONGO_URI': get_mongo_uri('MONGO_URI', MONGO_DB),
        'ELASTICSEARCH_INDEX': ELASTICSEARCH_INDEX,
        'AUTH_SERVER_SHARED_SECRET': AUTH_SERVER_SHARED_SECRET,
    }

    def context():
        pass

    context.app = None
    context.ctx = None
    context.client = None
    setup(context=context, config=test_config, app_factory=get_sd_app)

    return context.app


@pytest.fixture(scope='function')
def superdesk_app(request):
    """
    Superdesk app.

    :return: superdesk app
    :rtype: superdesk.factory.app.SuperdeskEve
    """

    return get_test_superdesk_app()


@pytest.fixture(scope='function')
def prodapi_app(request):
    """
    Prod api app.

    :return: prod api app
    :rtype: eve.flaskapp.Eve
    """

    return get_test_prodapi_app()


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
    clients_data = []

    if request.param:
        clients_data.append({
            "name": str(ObjectId()),  # just a random string
            "client_id": str(ObjectId()),
            "password": str(ObjectId()),  # just a random string
            "scope": request.param
        })
        with superdesk_app.app_context():
            RegisterClient().run(**clients_data[-1])

    return clients_data
