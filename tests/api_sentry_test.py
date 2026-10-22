import pytest

from superdesk import default_settings
from superdesk.flask import Config


@pytest.mark.parametrize("settings_module", ["prod_api.app.settings", "content_api.app.settings"])
def test_api_sentry_settings(settings_module):
    config = Config(".")
    config.from_object(settings_module)
    for key in ("SENTRY_DSN", "SENTRY_TRACES_SAMPLE_RATE", "SENTRY_PROFILES_SAMPLE_RATE"):
        assert config[key] == getattr(default_settings, key)
