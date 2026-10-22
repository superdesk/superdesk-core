import logging

import pytest

from superdesk import default_settings
from superdesk.errors import SuperdeskApiError
from superdesk.factory.app import set_error_handlers
from superdesk.flask import Config, Flask
from prod_api.app import set_prodapi_error_handlers


@pytest.mark.parametrize("api", ["prod_api", "content_api"])
def test_api_logging_defaults(api):
    config = Config(".")
    config.from_object(f"{api}.app.settings")
    for key in ("LOG_CONFIG_FILE", "GRAYLOG_HOST", "GRAYLOG_PORT", "GRAYLOG_FACILITY", "GRAYLOG_LEVEL"):
        assert config[key] == getattr(default_settings, key)


@pytest.mark.parametrize("api", ["prod_api", "content_api"])
@pytest.mark.parametrize(
    "error,status",
    [
        (RuntimeError("unhandled"), 500),
        (SuperdeskApiError.internalError("handled"), 500),
        (None, 500),
        (SuperdeskApiError.badRequestError("client error"), 400),
    ],
)
@pytest.mark.asyncio
async def test_api_error_logging(api, error, status, monkeypatch, caplog):
    app = Flask(f"logging_test_{api}")
    app.config.update(TESTING=False, DEBUG=False, PROPAGATE_EXCEPTIONS=False)
    set_error_handlers(app)
    if api == "prod_api":
        set_prodapi_error_handlers(app)

    async def render(resource, response):
        return "", response[-1]

    monkeypatch.setattr("superdesk.factory.app.send_response", render)
    monkeypatch.setattr("prod_api.app.send_response", render)

    @app.route("/error")
    async def error_endpoint():
        if error is None:
            try:
                raise OSError("asset save failed")
            except OSError as original:
                raise SuperdeskApiError.internalError("Saving file failed", exception=original)
        raise error

    with caplog.at_level(logging.ERROR):
        response = await app.test_client().get("/error")

    assert response.status_code == status
    records = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(records) == (1 if status == 500 else 0)
    if records:
        assert records[0].levelno == logging.ERROR
        assert records[0].exc_info is not None
        assert records[0].exc_info[2] is not None
        if error is None:
            assert isinstance(records[0].exc_info[1], OSError)
            assert str(records[0].exc_info[1]) == "asset save failed"


def test_api_error_logs_original_exception_without_request(caplog):
    try:
        raise OSError("asset save failed")
    except OSError as original:
        error = original

    with caplog.at_level(logging.ERROR):
        SuperdeskApiError.internalError("Saving file failed", exception=error)

    assert len(caplog.records) == 1
    assert caplog.records[0].exc_info == (type(error), error, error.__traceback__)
