from os import PathLike

from quart.app import RequestContext, AppContext

from superdesk.factory.app import SuperdeskApp, SuperdeskAsyncApp
from .http_client import TestClient


class TestFactory:
    base_db_name: str = "sptest"
    test_type: str | None = None
    default_settings_module: PathLike[str] | str | None = None
    config: dict | None = None
    config_backup: dict | None = None
    auto_add_apps: bool = True
    init_eve_resources: bool = True
    init_async_resources: bool = True
    init_request_context: bool = True
    init_app_context: bool = True

    async def get_app(self, config: dict) -> SuperdeskApp:
        raise NotImplementedError()

    async def after_all(self, context: "TestAppContext") -> None:
        ...

    async def before_module(self, context: "TestAppContext") -> None:
        raise NotImplementedError()

    async def after_module(self, context: "TestAppContext") -> None:
        ...

    async def before_test(self, context: "TestAppContext") -> None:
        ...

    async def after_test(self, context: "TestAppContext") -> None:
        ...

    # These next 2 are only supported in Behave
    async def before_step(self, context: "TestAppContext") -> None:
        ...

    async def after_step(self, context: "TestAppContext") -> None:
        ...


class TestAppContext:
    app: SuperdeskApp | None
    async_app: SuperdeskAsyncApp | None
    client: TestClient | None
    factory: TestFactory
    app_context: AppContext | None = None
    test_context: RequestContext | None = None


class NotificationMock:
    def __init__(self):
        self.messages = []
        self.client = None
        self.open = True

    def send(self, message, name):
        self.messages.append(message)

    def reset(self):
        self.messages = []
