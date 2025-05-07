import os
import asyncio
import contextvars
import traceback
import functools

import json
import pytest
from pathlib import Path
from bson import ObjectId
from requests.auth import _basic_auth_str

from superdesk.flask import url_for
from superdesk.tests import get_mongo_uri, setup, clean_dbs
from superdesk.factory import get_app as get_sd_app
from superdesk.auth_server.clients import RegisterClient
from prod_api.app import get_app as get_prodapi_api

from planning.prod_api.events.resource import EventsResource
from planning.events.events_schema import events_schema


MONGO_DB = "prodapi_tests"
ELASTICSEARCH_INDEX = MONGO_DB
AUTH_SERVER_SHARED_SECRET = "2kZOf0VI9T70vU9uMlKLyc5GlabxVgl6"


class Task311(asyncio.tasks.Task):
    """
    This is backport of Task from CPython 3.11
    It's needed to allow context passing
    """

    def __init__(self, coro, *, loop=None, name=None, context=None):
        super(asyncio.tasks.Task, self).__init__(loop=loop)
        if self._source_traceback:
            del self._source_traceback[-1]
        if not asyncio.coroutines.iscoroutine(coro):
            # raise after Future.__init__(), attrs are required for __del__
            # prevent logging for pending task in __del__
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        if name is None:
            self._name = f"Task-{asyncio.tasks._task_name_counter()}"
        else:
            self._name = str(name)

        self._num_cancels_requested = 0
        self._must_cancel = False
        self._fut_waiter = None
        self._coro = coro
        if context is None:
            self._context = contextvars.copy_context()
        else:
            self._context = context

        self._loop.call_soon(self._Task__step, context=self._context)
        asyncio.tasks._register_task(self)


class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def set_event_loop(self, loop):
        if loop is not None:
            context = contextvars.copy_context()
            loop.set_task_factory(functools.partial(task_factory, context=context))
        super().set_event_loop(loop)


def task_factory(loop, coro, context=None):
    stack = traceback.extract_stack()
    for frame in stack[-2::-1]:
        package_name = Path(frame.filename).parts[-2]
        if package_name != "asyncio":
            if package_name == "pytest_asyncio":
                # This function was called from pytest_asyncio, use shared context
                break
            else:
                # This function was called from somewhere else, create context copy
                context = None
            break
    return Task311(coro, loop=loop, context=context)


@pytest.fixture(scope="session")
def event_loop_policy(request):
    return CustomEventLoopPolicy()


async def get_test_prodapi_app(extra_config=None):
    """
    Create and return configured test prod api flask app.
    :param extra_config: extra settings
    :return: eve.flaskapp.Eve
    """
    test_config = {
        "TESTING": True,
        "SUPERDESK_TESTING": True,
        "MONGO_CONNECT": False,
        "MONGO_MAX_POOL_SIZE": 1,
        "MONGO_DBNAME": MONGO_DB,
        "MONGO_URI": get_mongo_uri("MONGO_URI", MONGO_DB),
        "ELASTICSEARCH_INDEX": ELASTICSEARCH_INDEX,
        "PRODAPI_URL": "http://localhost:5500",
        "MEDIA_PREFIX": "http://localhost:5500/prodapi/v1/assets",
        "PRODAPI_URL_PREFIX": "prodapi",
        "URL_PREFIX": "prodapi",
        "AUTH_SERVER_SHARED_SECRET": AUTH_SERVER_SHARED_SECRET,
    }
    if extra_config:
        test_config.update(extra_config)
    prodapi_app = get_prodapi_api(test_config)

    # patch Events API with dates schema
    # otherwise queries against it will fail (due to default sort)
    # this will not happen in a production environment
    # as the index/types should already be created
    EventsResource.schema = {"dates": events_schema["dates"]}

    # put elastic mapping
    async with prodapi_app.app_context():
        prodapi_app.data.elastic.init_index()

    return prodapi_app


async def get_test_superdesk_app(extra_config=None):
    """
    Create and return configured test superdesk flask app.
    :param extra_config: extra settings
    :return: eve.flaskapp.Eve
    """
    test_config = {
        "MONGO_DBNAME": MONGO_DB,
        "MONGO_URI": get_mongo_uri("MONGO_URI", MONGO_DB),
        "ELASTICSEARCH_INDEX": ELASTICSEARCH_INDEX,
        "AUTH_SERVER_SHARED_SECRET": AUTH_SERVER_SHARED_SECRET,
    }
    if extra_config:
        test_config.update(extra_config)

    def context():
        pass

    context.app = None
    context.ctx = None
    context.client = None
    await setup(context=context, config=test_config, app_factory=get_sd_app)

    return context.app


def teardown_app(app):
    """
    Drop test db and test app
    """
    clean_dbs(app)
    del app


@pytest.fixture(scope="function")
async def superdesk_app(request):
    """
    Superdesk app.

    :return: superdesk app
    :rtype: superdesk.factory.app.SuperdeskEve
    """

    extra_config = getattr(request, "param", {})
    app = await get_test_superdesk_app(extra_config)

    def test_app_teardown():
        """
        Drop test db and test app
        """
        teardown_app(app)

    request.addfinalizer(test_app_teardown)

    return app


@pytest.fixture(scope="function")
async def prodapi_app(request):
    """
    Prod api app.

    :return: prod api app
    :rtype: eve.flaskapp.Eve
    """

    extra_config = getattr(request, "param", {})
    app = await get_test_prodapi_app(extra_config)

    def test_app_teardown():
        """
        Drop test db and test app
        """
        teardown_app(app)

    request.addfinalizer(test_app_teardown)

    return app


@pytest.fixture(scope="module")
async def prodapi_app_with_data(request):
    """
    Prod api app with prefilled collections and with disabled auth.
    ATTENTION: This is a resource-heavy fixture and it's designed to use with "module" scope.
    It's better to use it in readonly tests and not modify data of fixtured app.

    :return: prod api app
    :rtype: eve.flaskapp.Eve
    """

    extra_config = getattr(request, "param", {})
    extra_config["PRODAPI_AUTH_ENABLED"] = False
    app = await get_test_prodapi_app(extra_config)

    # fill with data
    async with app.app_context():
        p = Path(os.path.join(os.path.dirname(__file__), "tests/fixtures"))
        for fixture_file in [x for x in p.iterdir() if x.is_file()]:
            with fixture_file.open() as f:
                app.data.insert(resource=fixture_file.stem, docs=json.loads(f.read()))

    def test_app_teardown():
        """
        Drop test db and test app
        """
        teardown_app(app)

    request.addfinalizer(test_app_teardown)

    return app


@pytest.fixture(scope="module")
async def prodapi_app_with_data_client(prodapi_app_with_data):
    """Test client for prod api with filled data"""

    client = prodapi_app_with_data.test_client()

    async with prodapi_app_with_data.app_context():
        yield client


@pytest.fixture(scope="function")
async def prodapi_client(prodapi_app):
    """Test client for prod api"""

    client = prodapi_app.test_client()

    async with prodapi_app.app_context():
        yield client


@pytest.fixture(scope="function")
async def superdesk_client(superdesk_app):
    """Test client for superdesk"""

    client = superdesk_app.test_client()

    async with superdesk_app.app_context():
        yield client


@pytest.fixture(scope="function")
async def auth_server_registered_clients(request, superdesk_app):
    """
    Registers clients for auth server.
    :return: dict with clients
    """
    clients_data = []

    async with superdesk_app.app_context():
        for param in request.param:
            # register clients
            clients_data.append(
                {
                    "name": str(ObjectId()),  # just a random string
                    "client_id": str(ObjectId()),
                    "password": str(ObjectId()),  # just a random string
                    "scope": param,
                }
            )
            await RegisterClient().run(**clients_data[-1])

    return clients_data


@pytest.fixture(scope="function")
async def issued_tokens(request, superdesk_app, superdesk_client):
    tokens = []
    clients_data = []

    # register clients
    async with superdesk_app.app_context():
        for param in request.param:
            clients_data.append(
                {
                    "name": str(ObjectId()),  # just a random string
                    "client_id": str(ObjectId()),
                    "password": str(ObjectId()),  # just a random string
                    "scope": param,
                }
            )
            await RegisterClient().run(**clients_data[-1])

    # retrieve tokens
    async with superdesk_app.test_request_context("/"):
        for client_data in clients_data:
            resp = superdesk_client.post(
                url_for("auth_server.issue_token"),
                data={"grant_type": "client_credentials"},
                headers={"Authorization": _basic_auth_str(client_data["client_id"], client_data["password"])},
            )
            tokens.append(json.loads(resp.data.decode("utf-8")))

    teardown_app(superdesk_app)
    del superdesk_client

    return tokens
