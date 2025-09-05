import logging
from copy import deepcopy
import os
from pathlib import Path
from importlib import import_module

from quart import Quart, Config

from .common import TestAppContext, NotificationMock, TestFactory
from .http_client import TestClient
from .resources import close_all_db_connections, drop_all_db_databases, delete_all_db_documents, init_db_indexes
from .mongo import get_mongo_uri


logger = logging.getLogger(__name__)


class TestAppFactory(TestFactory):
    async def before_module(self, context: TestAppContext) -> None:
        setup_logging()
        await close_all_db_connections(context)
        await create_app(context)
        drop_all_db_databases(context)
        init_db_indexes(context)

        if context.factory.init_app_context:
            context.app_context = context.app.app_context()
            await context.app_context.push()

        if context.factory.init_request_context:
            context.test_context = context.app.test_request_context("/")
            await context.test_context.push()

    async def after_module(self, context: TestAppContext) -> None:
        if context.test_context:
            try:
                await context.test_context.pop()
            except LookupError:
                pass
        if context.app_context:
            try:
                await context.app_context.pop()
            except LookupError:
                pass

        for name in context.app.config["BLUEPRINTS"]:
            mod = import_module(name)
            if getattr(mod, "blueprint"):
                mod.blueprint._got_registered_once = False

    async def before_test(self, context: TestAppContext) -> None:
        if context.factory.config_backup is not None:
            context.app.config.update(context.factory.config_backup)

        async with context.app.app_context():
            delete_all_db_documents(context)

        # context.app_context = context.app.app_context()
        # await context.app_context.push()

        # context.test_context = context.app.test_request_context("/")
        # await context.test_context.push()

        # Reset the context headers, used by the client
        context.headers = [("Content-Type", "application/json"), ("Origin", "localhost")]

    # TODO-PR: Fix this one
    # async def after_test(self, context: TestAppContext) -> None:
    #     await context.app_context.pop()
    #     await context.test_context.pop()


def setup_logging() -> None:
    current_log_level = logging.getLogger().getEffectiveLevel()
    log_names: set[str] = {
        "superdesk.websockets_comms",
        "apps",
        "elastic",
        "urllib3",
        "celery",
        "superdesk.errors",
        "superdesk",
        "elasticsearch",
        "newsroom",
    }
    for log_name in log_names:
        logging.getLogger(log_name).setLevel(current_log_level)


async def create_app(context: TestAppContext) -> None:
    app_config = setup_config(context, {})
    app_config.update(deepcopy(context.factory.config))

    context.app_context = None
    context.test_context = None
    app = await context.factory.get_app(app_config)
    context.app = app
    context.async_app = app.async_app
    app.test_client_class = TestClient
    context.client = app.test_client()
    context.factory.config_backup = deepcopy(app.config)


def setup_mock_notifications(context: TestAppContext) -> None:
    mock = NotificationMock()
    if context.app.notification_client:
        mock.client = context.app.notification_client
    context.app.notification_client = mock


def get_prefixed_url(current_app: Quart, endpoint: str) -> str:
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint

    endpoint = endpoint.lstrip("/")
    url_prefix = current_app.config["URL_PREFIX"] + "/"
    if endpoint.startswith(url_prefix):
        return endpoint
    return url_prefix + endpoint


def setup_config(context: TestAppContext, config: dict) -> dict:
    app_abspath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app_config = Config(app_abspath)
    app_config.from_object(context.factory.default_settings_module or "superdesk.default_settings")
    app_config = deepcopy(app_config)

    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        settings = p / "settings.py"
        if settings.is_file():
            logger.info(f"using local settings from {settings}")
            app_config.from_pyfile(settings)
            break
    else:
        logger.warning("Can't find local settings")

    update_config(context, app_config)

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

    return {key: deepcopy(val) for key, val in app_config.items()}


def update_config(context: TestAppContext, conf, include_planning: bool = True) -> dict:
    base_db_name = context.factory.base_db_name
    conf["ELASTICSEARCH_INDEX"] = base_db_name
    conf["MONGO_DBNAME"] = base_db_name
    conf["MONGO_URI"] = get_mongo_uri("MONGO_URI", base_db_name)
    conf["LEGAL_ARCHIVE_DBNAME"] = f"{base_db_name}_legal_archive"
    conf["LEGAL_ARCHIVE_URI"] = get_mongo_uri("LEGAL_ARCHIVE_URI", f"{base_db_name}_legal_archive")
    conf["ARCHIVED_DBNAME"] = f"{base_db_name}_archived"
    conf["ARCHIVED_URI"] = get_mongo_uri("ARCHIVED_URI", f"{base_db_name}_archived")
    conf["CONTENTAPI_URL"] = "http://localhost:5400"
    conf["CONTENTAPI_MONGO_DBNAME"] = f"{base_db_name}_contentapi"
    conf["CONTENTAPI_MONGO_URI"] = get_mongo_uri("CONTENTAPI_MONGO_URI", f"{base_db_name}_contentapi")
    conf["CONTENTAPI_ELASTICSEARCH_INDEX"] = f"{base_db_name}_contentapi"

    conf["DEBUG"] = True
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
        "archived": f"{base_db_name}_archived",
        "archive": f"{base_db_name}_archive",
        "ingest": f"{base_db_name}_ingest",
    }

    # (behave|nose)tests depends from these settings
    conf["DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES"] = "AAP"
    conf["MACROS_MODULE"] = "superdesk.macros"
    conf["BABEL_DEFAULT_TIMEZONE"] = "Europe/Prague"
    conf["DEFAULT_TIMEZONE"] = "Europe/Prague"
    conf["LEGAL_ARCHIVE"] = True

    if context.factory.auto_add_apps:
        conf["INSTALLED_APPS"].extend(["superdesk.macros.imperial", "apps.rundowns", "apps.user_availability"])

        if include_planning:
            conf["INSTALLED_APPS"].append("planning")
            conf["MODULES"].append("planning")

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
