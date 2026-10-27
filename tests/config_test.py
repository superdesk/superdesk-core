import os
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import pytest

from superdesk import default_settings
from superdesk.download import bp, download_url
from superdesk.factory.app import SuperdeskEve, get_app
from superdesk.flask import Config, Flask


class TestConfig:
    X = True


class ConfigTestCase(unittest.TestCase):
    def test_config_update(self):
        config = Config(os.path.abspath(os.path.dirname(__file__)))
        config.update({"X": True})
        self.assertTrue(config.get("X"))
        config.update({"X": False})
        self.assertFalse(config.get("X"))
        config.from_object(TestConfig())
        self.assertTrue(config.get("X"))


@pytest.fixture
def factory_app():
    apps = []
    with patch("superdesk.app"), patch("superdesk.core.app._global_app", None):

        def create(config=None, config_object=None):
            app = get_app(
                config={"CORE_APPS": [], "INSTALLED_APPS": [], "MODULES": [], **(config or {})},
                config_object=config_object,
            )
            apps.append(app)
            return app

        yield create
        for app in apps:
            app.async_app.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override_source, overrides, expected_scheme",
    [
        ("config", {"SERVER_URL": "https://news.example.com/api"}, "https"),
        ("config_object", {"SERVER_URL": "https://news.example.com/api"}, "https"),
        ("config", {"SERVER_URL": "http://news.example.com/api"}, "http"),
        ("config", {"SERVER_URL": "https://news.example.com/api", "PREFERRED_URL_SCHEME": "http"}, "http"),
        ("config", {"SERVER_URL": "https://news.example.com/api", "PREFERRED_URL_SCHEME": None}, None),
    ],
)
async def test_factory_download_scheme_after_application_overrides(
    factory_app, override_source, overrides, expected_scheme
):
    with patch.dict(default_settings.__dict__):
        default_settings.SERVER_URL = "http://localhost:5000/api"
        default_settings.__dict__.pop("PREFERRED_URL_SCHEME", None)
        if override_source == "config":
            app = factory_app(config=overrides)
        else:
            app = factory_app(config_object=SimpleNamespace(**overrides))
    assert app.config["PREFERRED_URL_SCHEME"] == expected_scheme
    app.register_blueprint(bp, url_prefix="/api")
    async with app.test_request_context("/api/export", scheme="http"):
        actual_scheme = expected_scheme or "http"
        assert download_url("export-test") == f"{actual_scheme}://localhost/api/download/export-test"


@pytest.mark.asyncio
async def test_download_url_preserves_https_request_without_preference():
    app = Flask(__name__)
    app.config.pop("PREFERRED_URL_SCHEME", None)
    app.register_blueprint(bp, url_prefix="/api")
    factory_app = Mock(spec=SuperdeskEve, config=app.config)
    expected_url = "https://localhost/api/download/export-test"
    async with app.test_request_context("/api/export", scheme="https"):
        assert download_url("export-test") == expected_url
        assert SuperdeskEve.download_url(factory_app, "export-test") == expected_url
