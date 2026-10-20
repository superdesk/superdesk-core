import os
import runpy
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "server_url, preferred_scheme, expected_scheme",
    [
        ("http://news.example.com/api", None, "http"),
        ("https://news.example.com/api", None, "https"),
        ("http://localhost:5000/api", None, "http"),
        ("http://127.0.0.1:5000/api", None, "http"),
        ("http://[::1]:5000/api", None, "http"),
        ("https://localhost:5000/api", None, "https"),
        ("http://localhost.example.com/api", None, "http"),
        ("http://news.example.com/api", "http", "http"),
        ("http://localhost:5000/api", "https", "https"),
    ],
)
async def test_default_download_url_scheme(factory_app, server_url, preferred_scheme, expected_scheme):
    environment = {"SUPERDESK_URL": server_url}
    if preferred_scheme is not None:
        environment["PREFERRED_URL_SCHEME"] = preferred_scheme
    with patch.dict(os.environ, environment, clear=True):
        config = runpy.run_path(default_settings.__file__)

    app = factory_app(config_object=SimpleNamespace(**config))
    assert app.config["PREFERRED_URL_SCHEME"] == expected_scheme
    app.register_blueprint(bp, url_prefix="/api")
    async with app.test_request_context("/api/export", scheme="http"):
        assert download_url("export-test") == f"{expected_scheme}://localhost/api/download/export-test"


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
@pytest.mark.parametrize("override_source", ["config", "config_object"])
@pytest.mark.parametrize("preferred_scheme", ["missing", None, "http", "https"])
async def test_factory_download_scheme_after_application_overrides(factory_app, override_source, preferred_scheme):
    overrides = {"SERVER_URL": "https://news.example.com/api"}
    if preferred_scheme != "missing":
        overrides["PREFERRED_URL_SCHEME"] = preferred_scheme
    with patch.dict(default_settings.__dict__):
        default_settings.SERVER_URL = "http://localhost:5000/api"
        default_settings.__dict__.pop("PREFERRED_URL_SCHEME", None)
        if override_source == "config":
            app = factory_app(config=overrides)
        else:
            app = factory_app(config_object=SimpleNamespace(**overrides))
    expected_scheme = "https" if preferred_scheme == "missing" else preferred_scheme
    assert app.config["PREFERRED_URL_SCHEME"] == expected_scheme
    app.register_blueprint(bp, url_prefix="/api")
    async with app.test_request_context("/api/export", scheme="http"):
        actual_scheme = expected_scheme or "http"
        assert download_url("export-test") == f"{actual_scheme}://localhost/api/download/export-test"


@pytest.mark.asyncio
@pytest.mark.parametrize("request_scheme", ["http", "https"])
@pytest.mark.parametrize("preferred_scheme", ["missing", None, "http", "https"])
async def test_download_url_scheme_precedence(request_scheme, preferred_scheme):
    app = Flask(__name__)
    if preferred_scheme == "missing":
        app.config.pop("PREFERRED_URL_SCHEME", None)
    else:
        app.config["PREFERRED_URL_SCHEME"] = preferred_scheme
    app.register_blueprint(bp, url_prefix="/api")
    factory_app = Mock(spec=SuperdeskEve, config=app.config)
    expected_scheme = request_scheme if preferred_scheme in ("missing", None) else preferred_scheme
    expected_url = f"{expected_scheme}://localhost/api/download/export-test"
    async with app.test_request_context("/api/export", scheme=request_scheme):
        assert download_url("export-test") == expected_url
        assert SuperdeskEve.download_url(factory_app, "export-test") == expected_url
