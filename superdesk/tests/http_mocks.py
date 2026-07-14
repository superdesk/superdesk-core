from typing import Any, Literal, Callable
from functools import partial
import re

from yarl import URL
from aioresponses import aioresponses, CallbackResult

from superdesk.core.types import HTTP_METHOD


HttpMockCallback = Callable[[str], CallbackResult]
HttpMocks = dict[Literal["*"] | str, dict[tuple[HTTP_METHOD | Literal["*"], str], HttpMockCallback]]


__all__ = [
    "mock_http",
    "mock_multiple_endpoints",
    "CallbackResult",
]


def mock_http(context: Any) -> aioresponses:
    try:
        mock: None | aioresponses = getattr(context, "_http_mock", None)
    except KeyError:
        mock = None

    if mock is not None:
        return mock

    mock = aioresponses(passthrough=["http://127.0.0.1", "http://localhost"])
    mock.start()
    setattr(context, "_http_mock", mock)

    def stop_mock():
        mock.stop()
        setattr(context, "_http_mock", None)

    if hasattr(context, "addCleanup"):
        # Pytest style
        context.addCleanup(stop_mock)
    elif hasattr(context, "add_cleanup"):
        # Behave style
        context.add_cleanup(stop_mock)

    return mock


def mock_multiple_endpoints(context: Any, http_mocks: HttpMocks | Exception | CallbackResult) -> aioresponses:
    methods: list[HTTP_METHOD] = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    mock = mock_http(context)

    def _mock_requests(request_method: HTTP_METHOD, request_url: URL, **kwargs) -> CallbackResult:
        if isinstance(http_mocks, Exception):
            raise http_mocks
        elif isinstance(http_mocks, CallbackResult):
            return http_mocks

        host_mocks = http_mocks.get(request_url.host or "") or http_mocks.get("*") or {}
        for (http_method, path_prefix), callback in host_mocks.items():
            if http_method in ("*", request_method) and (
                path_prefix == "*" or request_url.path.startswith(path_prefix)
            ):
                return callback(str(request_url))

        return CallbackResult(status=404, body="Mock didn't match any requests", content_type="text/plain")

    for method in methods:
        mock.add(
            re.compile(r".*"),
            method,
            callback=partial(_mock_requests, method),
            repeat=True,
        )

    return mock
