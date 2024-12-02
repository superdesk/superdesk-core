# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Tuple
import os
import functools
import logging
import socket
from pathlib import Path
from dataclasses import dataclass

from copy import deepcopy
from unittest.mock import patch
from unittest import IsolatedAsyncioTestCase
from quart import Response
from quart.testing import QuartClient
from werkzeug.datastructures import Authorization

from superdesk.core import json
from superdesk.flask import Config
from apps.ldap import ADAuth
from superdesk import get_resource_service
from superdesk.cache import cache
from superdesk.factory import get_app
from superdesk.factory.app import get_media_storage_class, SuperdeskApp
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core import app as core_app
from superdesk.core.resources import ResourceModel
from superdesk.storage.amazon_media_storage import AmazonMediaStorage
from superdesk.storage.proxy import ProxyMediaStorage
from superdesk.types import User


logger = logging.getLogger(__name__)
test_user = {
    "username": "test_user",
    "password": "test_password",
    "is_active": True,
    "is_enabled": True,
    "needs_activation": False,
    "sign_off": "abc",
    "email": "behave_test@sourcefabric.org",
    "preferences": {
        "email:notification": {
            "type": "bool",
            "default": True,
            "enabled": True,
        }
    },
}


def get_mongo_uri(key, dbname):
    """Read mongo uri from env variable and replace dbname.

    :param key: env variable name
    :param dbname: mongo db name to use
    """
    env_uri = os.environ.get(key, "mongodb://localhost/test")
    env_host = env_uri.rsplit("/", 1)[0]
    return "/".join([env_host, dbname])


def update_config(conf, auto_add_apps: bool = True):
    conf["ELASTICSEARCH_INDEX"] = "sptest"
    conf["MONGO_DBNAME"] = "sptests"
    conf["MONGO_URI"] = get_mongo_uri("MONGO_URI", "sptests")
    conf["LEGAL_ARCHIVE_DBNAME"] = "sptests_legal_archive"
    conf["LEGAL_ARCHIVE_URI"] = get_mongo_uri("LEGAL_ARCHIVE_URI", "sptests_legal_archive")
    conf["ARCHIVED_DBNAME"] = "sptests_archived"
    conf["ARCHIVED_URI"] = get_mongo_uri("ARCHIVED_URI", "sptests_archived")
    conf["CONTENTAPI_URL"] = "http://localhost:5400"
    conf["CONTENTAPI_MONGO_DBNAME"] = "sptests_contentapi"
    conf["CONTENTAPI_MONGO_URI"] = get_mongo_uri("CONTENTAPI_MONGO_URI", "sptests_contentapi")
    conf["CONTENTAPI_ELASTICSEARCH_INDEX"] = "sptest_contentapi"

    conf["TESTING"] = True
    conf["SUPERDESK_TESTING"] = True
    conf["BCRYPT_GENSALT_WORK_FACTOR"] = 4
    conf["CELERY_TASK_ALWAYS_EAGER"] = True
    conf["CELERY_BEAT_SCHEDULE_FILENAME"] = "./testschedule.db"
    conf["CELERY_BEAT_SCHEDULE"] = {}
    conf["CONTENT_EXPIRY_MINUTES"] = 99
    conf["SECRET_KEY"] = "test-secret"
    conf["JSON_SORT_KEYS"] = True
    conf["ELASTICSEARCH_INDEXES"] = {
        "archived": "sptest_archived",
        "archive": "sptest_archive",
        "ingest": "sptest_ingest",
    }

    # (behave|nose)tests depends from these settings
    conf["DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES"] = "AAP"
    conf["MACROS_MODULE"] = "superdesk.macros"
    conf["DEFAULT_TIMEZONE"] = "Europe/Prague"
    conf["LEGAL_ARCHIVE"] = True
    if auto_add_apps:
        conf["INSTALLED_APPS"].extend(["planning", "superdesk.macros.imperial", "apps.rundowns"])

    # limit mongodb connections
    conf["MONGO_CONNECT"] = False
    conf["ARCHIVED_CONNECT"] = False
    conf["LEGAL_ARCHIVE_CONNECT"] = False
    conf["MONGO_MAX_POOL_SIZE"] = 1
    conf["ARCHIVED_MAX_POOL_SIZE"] = 1
    conf["LEGAL_ARCHIVE_MAX_POOL_SIZE"] = 1

    # misc
    conf["GEONAMES_USERNAME"] = "superdesk_dev"
    conf["PUBLISH_ASSOCIATED_ITEMS"] = True
    conf["PAGINATION_LIMIT"] = conf["PAGINATION_DEFAULT"] = 200
    conf["RUNDOWNS_SCHEDULE_HOURS"] = 24
    conf["RUNDOWNS_TIMEZONE"] = "Europe/Prague"

    # auth server
    conf["AUTH_SERVER_SHARED_SECRET"] = "some secret"

    # todo: only activate it for specific tests
    conf["BACKEND_FIND_ONE_SEARCH_TEST"] = True

    conf["PROXY_MEDIA_STORAGE_CHECK_EXISTS"] = True

    return conf


def drop_elastic(app):
    with app.app_context():
        app.data.elastic.drop_index()


def foreach_mongo(fn):
    """
    Run the same actions on all mongo databases

    This decorator adds two additional parameters to called function
    `dbconn` and `dbname` for using proper connection and database name
    """

    @functools.wraps(fn)
    def inner(app, *a, **kw):
        pairs = (
            ("MONGO", "MONGO_DBNAME"),
            ("ARCHIVED", "ARCHIVED_DBNAME"),
            ("LEGAL_ARCHIVE", "LEGAL_ARCHIVE_DBNAME"),
            ("CONTENTAPI_MONGO", "CONTENTAPI_MONGO_DBNAME"),
        )
        with app.app_context():
            for prefix, name in pairs:
                if not app.config.get(name):
                    continue
                kw["dbname"] = app.config[name]
                kw["dbconn"] = app.data.mongo.pymongo(prefix=prefix).cx
                fn(app, *a, **kw)

    return inner


async def drop_mongo(app):
    pairs = (
        ("MONGO", "MONGO_DBNAME"),
        ("ARCHIVED", "ARCHIVED_DBNAME"),
        ("LEGAL_ARCHIVE", "LEGAL_ARCHIVE_DBNAME"),
        ("CONTENTAPI_MONGO", "CONTENTAPI_MONGO_DBNAME"),
    )
    async with app.app_context():
        for prefix, name in pairs:
            if not app.config.get(name):
                continue
            dbname = app.config[name]
            dbconn = app.data.mongo.pymongo(prefix=prefix).cx
            dbconn.drop_database(dbname)


def setup_config(config, auto_add_apps: bool = True):
    app_abspath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app_config = Config(app_abspath)
    app_config.from_object("superdesk.default_settings")
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        settings = p / "settings.py"
        if settings.is_file():
            logger.info(f"using local settings from {settings}")
            app_config.from_pyfile(settings)
            break
    else:
        logger.warning("Can't find local settings")

    update_config(app_config, auto_add_apps)

    app_config.setdefault("INSTALLED_APPS", [])

    # Extend the INSTALLED APPS with the list provided
    if config:
        config.setdefault("INSTALLED_APPS", [])
        app_config["INSTALLED_APPS"].extend(config.pop("INSTALLED_APPS", []))

    # Make sure there are no duplicate entries in INSTALLED_APPS
    app_config["INSTALLED_APPS"] = list(set(app_config["INSTALLED_APPS"]))

    app_config.update(
        config or {},
        **{
            "APP_ABSPATH": app_abspath,
            "TESTING": True,
        },
    )

    logging.getLogger("apps").setLevel(logging.WARNING)
    logging.getLogger("elastic").setLevel(logging.WARNING)  # elastic datalayer
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("superdesk").setLevel(logging.ERROR)
    logging.getLogger("elasticsearch").setLevel(logging.ERROR)
    logging.getLogger("superdesk.errors").setLevel(logging.ERROR)

    return {key: deepcopy(val) for key, val in app_config.items()}


def update_config_from_step(context, config):
    context.app.config.update(config)

    if "MEDIA_STORAGE_PROVIDER" in config or "AMAZON_CONTAINER_NAME" in config:
        context.app.media = get_media_storage_class(context.app.config)(context.app)

    if "AMAZON_CONTAINER_NAME" in config:
        if isinstance(context.app.media, AmazonMediaStorage):
            m = patch.object(context.app.media, "client")
            m.start()
        elif isinstance(context.app.media, ProxyMediaStorage):
            m = patch.object(context.app.media.storage(), "client")
            m.start()


async def clean_dbs(app, force=False):
    await _clean_es(app)
    await drop_mongo(app)


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


async def _clean_es(app):
    async with app.app_context():
        app.data.elastic.drop_index()


@retry(socket.timeout, 2)
async def clean_es(app, force=False):
    use_snapshot(app, "clean", [snapshot_es], force)(_clean_es)(app)


def snapshot(fn):
    """
    Call create or restore snapshot function
    """

    @functools.wraps(fn)
    def inner(app, name, action, **kw):
        assert action in ["create", "restore"]
        create, restore = fn(app, name, **kw)
        {"create": create, "restore": restore}[action]()

    return inner


@snapshot
def snapshot_es(app, name):
    indices = "%s*" % app.config["ELASTICSEARCH_INDEX"]
    backup = ("backups", "%s%s" % (indices[:-1], name))
    es = app.data.elastic.es

    def create():
        es.snapshot.delete(*backup, ignore=[404])
        es.indices.open(indices, expand_wildcards="closed", ignore=[404])
        es.snapshot.create(
            *backup,
            wait_for_completion=True,
            body={
                "indices": indices,
                "allow_no_indices": False,
            },
        )

    def restore():
        es.indices.close(indices, expand_wildcards="open", ignore=[404])
        es.snapshot.restore(*backup, body={"indices": indices, "allow_no_indices": False}, wait_for_completion=True)

    return create, restore


@foreach_mongo
@snapshot
def snapshot_mongo(app, name, dbconn, dbname):
    snapshot = "%s_%s" % (dbname, name)

    def create():
        dbconn.drop_database(snapshot)
        dbconn.admin.command("copydb", fromdb=dbname, todb=snapshot)

    def restore():
        dbconn.drop_database(dbname)
        dbconn.admin.command("copydb", fromdb=snapshot, todb=dbname)

    return create, restore


def use_snapshot(app, name, funcs=(snapshot_es, snapshot_mongo), force=False):
    def snapshot(action):
        for f in funcs:
            f(app, name, action=action)

    def wrapper(fn):
        path = app.config.get("ELASTICSEARCH_BACKUPS_PATH")
        enabled = path and os.path.exists(path)

        @functools.wraps(fn)
        def inner(*a, **kw):
            if not enabled or force:
                logger.debug("Don't use snapshot for %s; enabled=%s; force=%s", fn, enabled, force)
                use_snapshot.cache.pop(fn, None)
                return fn(*a, **kw)

            if fn in use_snapshot.cache:
                snapshot("restore")
                logger.debug("Restore snapshot for %s", fn)
            else:
                use_snapshot.cache[fn] = fn(*a, **kw)
                snapshot("create")
                logger.debug("Create snapshot for %s", fn)
            return use_snapshot.cache[fn]

        return inner

    return wrapper


use_snapshot.cache = {}  # type: ignore


async def stop_previous_app():
    if not hasattr(setup, "async_app") and not hasattr(setup, "app"):
        return

    if hasattr(setup, "async_app"):
        async_app: SuperdeskAsyncApp | None = getattr(setup, "async_app", None)

        for resource_name, resource_config in async_app.mongo.get_all_resource_configs().items():
            client, db = async_app.mongo.get_client_async(resource_name)
            await client.drop_database(db)

        async_app.elastic.drop_indexes()
        await async_app.elastic.stop()

        for service in async_app.resources._resource_services:
            if hasattr(service, "_instance"):
                del service._instance

        async_app.stop()
        del setup.async_app

    if hasattr(setup, "app"):
        app: SuperdeskApp | None = getattr(setup, "app", None)

        # Close all PyMongo Connections (new ones will be created with ``app_factory`` call)
        for key, val in app.extensions["pymongo"].items():
            val[0].close()

        app.extensions["pymongo"] = {}
        del setup.app


async def setup(context=None, config=None, app_factory=get_app, reset=False, auto_add_apps: bool = True):
    if not hasattr(setup, "app") or hasattr(setup, "reset") or config:  # type: ignore[attr-defined]
        cfg = setup_config(config, auto_add_apps)
        setup.app = app_factory(cfg)  # type: ignore[attr-defined]
        setup.reset = reset  # type: ignore[attr-defined]
    app = setup.app  # type: ignore[attr-defined]

    if context:
        context.app = app
        context.client = app.test_client()
        if not hasattr(context, "BEHAVE") and not hasattr(context, "test_context"):
            context.test_context = app.test_request_context("/")
            context.test_context.push()

    async with app.app_context():
        await clean_dbs(app, force=bool(config))
        app.data.elastic.init_index()
        cache.clean()


async def setup_auth_user(context, user=None):
    await setup_db_user(context, user)


def token_to_basic_auth_header(token: str) -> Tuple[str, str]:
    """
    Use werkzeug's Authorization to create a valid basic auth token. This way we don't
    need to know how quart/werkzeug handles it convertion to string internally
    """
    basic_auth = Authorization("basic", data=dict(username=token, password=""))
    return ("Authorization", basic_auth.to_header())  # type: ignore[attr-defined]


def add_user_info_to_context(context: Any, token: str, user: User, auth_id=None):
    """
    Add current user's session information to context headers.
    It converts the plain string token into a valid basic auth token that
    will be converted back to string (internal) by quart/werkzeug Request.
    """
    basic_token_header = token_to_basic_auth_header(token)
    context.headers.append(basic_token_header)

    if getattr(context, "user", None):
        context.previous_user = context.user
    context.user = user

    set_placeholder(context, "CONTEXT_USER_ID", str(user.get("_id")))
    set_placeholder(context, "AUTH_ID", str(auth_id))


def set_placeholder(context, name, value):
    old_p = getattr(context, "placeholders", None)
    if not old_p:
        context.placeholders = dict()
    context.placeholders[name] = value


def get_prefixed_url(current_app, endpoint):
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint

    endpoint = endpoint.lstrip("/")
    url_prefix = current_app.config["URL_PREFIX"] + "/"
    if endpoint.startswith(url_prefix):
        return endpoint
    return url_prefix + endpoint


async def setup_db_user(context, user):
    """Setup the user for the DB authentication.

    :param context: test context
    :param dict user: user
    """
    user = user or test_user
    async with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        original_password = user["password"]

        user.setdefault("user_type", "administrator")

        if not get_resource_service("users").find_one(username=user["username"], req=None):
            get_resource_service("users").post([user])

        user["password"] = original_password
        auth_data = json.dumps({"username": user["username"], "password": user["password"]})
        auth_response = await context.client.post(
            get_prefixed_url(context.app, "/auth_db"), data=auth_data, headers=context.headers
        )

        auth_data = json.loads(await auth_response.get_data())
        token = auth_data.get("token")
        auth_id = auth_data.get("_id")
        add_user_info_to_context(context, token, user, auth_id)


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
    ad_user["email"] = "mock@mail.com.au"

    ad_user.setdefault("user_type", "administrator")

    # ad profile to be return from the patch object
    ad_profile = {
        "email": ad_user["email"],
        "username": ad_user["username"],
        # so that test run under the administrator context.
        "user_type": ad_user.get("user_type"),
        "sign_off": ad_user.get("sign_off", "abc"),
        "preferences": {
            "email:notification": {
                "type": "bool",
                "default": True,
                "enabled": True,
            }
        },
    }

    with patch.object(ADAuth, "authenticate_and_fetch_profile", return_value=ad_profile):
        auth_data = json.dumps({"username": ad_user["username"], "password": ad_user["password"]})
        auth_response = context.client.post(
            get_prefixed_url(context.app, "/auth_db"), data=auth_data, headers=context.headers
        )
        auth_response_as_json = json.loads(auth_response.get_data())
        token = auth_response_as_json.get("token").encode("ascii")
        ad_user["_id"] = auth_response_as_json["user"]

        add_user_info_to_context(context, token, ad_user)


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


@dataclass
class MockWSGI:
    config: Dict[str, Any]

    def add_url_rule(self, *args, **kwargs):
        pass

    def register_endpoint(self, endpoint):
        pass


class AsyncTestCase(IsolatedAsyncioTestCase):
    app: SuperdeskAsyncApp
    app_config: Dict[str, Any] = {}
    autorun: bool = True

    def setupApp(self):
        self.app_config = setup_config(deepcopy(self.app_config))
        self.app = SuperdeskAsyncApp(MockWSGI(config=self.app_config))
        setattr(setup, "async_app", self.app)
        self.startApp()

    def startApp(self):
        self.app.start()

    async def asyncSetUp(self):
        if not self.autorun:
            return

        self.setupApp()
        self.addAsyncCleanup(stop_previous_app)

    def get_fixture_path(self, filename):
        rootpath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(rootpath, "features", "steps", "fixtures", filename)

    def assertDictContains(self, source: dict, contains: dict):
        self.assertDictEqual({key: val for key, val in source.items() if key in contains}, contains)


class TestClient(QuartClient):
    def model_instance_to_json(self, model_instance: ResourceModel):
        return model_instance.to_dict(mode="json")

    async def post(self, *args, **kwargs) -> Response:
        if "json" in kwargs:
            if isinstance(kwargs["json"], ResourceModel):
                kwargs["json"] = self.model_instance_to_json(kwargs["json"])
            elif isinstance(kwargs["json"], list):
                kwargs["json"] = [
                    self.model_instance_to_json(item) if isinstance(item, ResourceModel) else item
                    for item in kwargs["json"]
                ]
            elif isinstance(kwargs["json"], dict):
                kwargs["json"] = {
                    key: self.model_instance_to_json(value) if isinstance(value, ResourceModel) else value
                    for key, value in kwargs["json"].items()
                }

        return await super().post(*args, **kwargs)


class AsyncFlaskTestCase(AsyncTestCase):
    async_app: SuperdeskAsyncApp
    app: SuperdeskApp
    use_default_apps: bool = False

    async def asyncSetUp(self):
        config = deepcopy(self.app_config)

        if self.use_default_apps:
            await setup(self, config=config, reset=True, auto_add_apps=True)
        else:
            config.setdefault("CORE_APPS", [])
            config.setdefault("INSTALLED_APPS", [])
            await setup(self, config=config, reset=True, auto_add_apps=False)
        self.async_app = self.app.async_app
        setattr(setup, "async_app", self.async_app)
        self.app.test_client_class = TestClient
        self.test_client = self.app.test_client()
        self.ctx = self.app.app_context()
        await self.ctx.push()

        async def clean_ctx():
            if self.ctx:
                try:
                    await self.ctx.pop()
                except Exception:
                    pass

        self.addAsyncCleanup(clean_ctx)
        self.addAsyncCleanup(stop_previous_app)
        self.async_app.elastic.init_all_indexes()

    async def get_resource_etag(self, resource: str, item_id: str):
        return (await (await self.test_client.get(f"/api/{resource}/{item_id}")).get_json())["_etag"]

    async def resetDatabase(self):
        await clean_dbs(self.app)
        self.app.data.elastic.init_index()
        cache.clean()


class TestCase(AsyncFlaskTestCase):
    use_default_apps: bool = True
