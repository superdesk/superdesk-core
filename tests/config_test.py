import os
import runpy
import unittest
from unittest.mock import Mock, patch

import pytest

from superdesk import default_settings
from superdesk.download import bp, download_url
from superdesk.factory.app import SuperdeskEve
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
        ("http://news.example.com/api", None, "https"),
        ("https://news.example.com/api", None, "https"),
        ("http://localhost:5000/api", None, "http"),
        ("http://127.0.0.1:5000/api", None, "http"),
        ("http://[::1]:5000/api", None, "http"),
        ("https://localhost:5000/api", None, "https"),
        ("http://localhost.example.com/api", None, "https"),
        ("http://news.example.com/api", "http", "http"),
        ("http://localhost:5000/api", "https", "https"),
    ],
)
async def test_default_download_url_scheme(server_url, preferred_scheme, expected_scheme):
    environment = {"SUPERDESK_URL": server_url}
    if preferred_scheme is not None:
        environment["PREFERRED_URL_SCHEME"] = preferred_scheme
    with patch.dict(os.environ, environment, clear=True):
        config = runpy.run_path(default_settings.__file__)

    assert config["PREFERRED_URL_SCHEME"] == expected_scheme
    app = Flask(__name__)
    app.config["PREFERRED_URL_SCHEME"] = config["PREFERRED_URL_SCHEME"]
    app.register_blueprint(bp, url_prefix="/api")
    async with app.test_request_context("/api/export", scheme="http"):
        assert download_url("export-test") == f"{expected_scheme}://localhost/api/download/export-test"


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
