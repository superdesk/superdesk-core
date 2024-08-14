from typing import List, Optional, Dict, Any, cast
import requests

from quart.typing import ResponseTypes

from superdesk import __version__ as superdesk_version
from superdesk.core import get_app_config, get_current_app
from superdesk.flask import request, make_response, Flask
from superdesk.utils import get_cors_headers


class HTTPProxy:
    """A class for proxying HTTP requests to an external service.

    Attributes
    ----------
    endpoint_name : str
        The endpoint name used when registering the proxy with Flask (used in ``url_for``)
    internal_url : str
        The internal URL used to proxy requests from
    external_url : str
        The external URL used to proxy the requests to
    http_methods: list[str]
        list of HTTP methods allowed for this proxy
    auth: bool
        If ``True`` (the default), then this proxy is available only to authenticated users
    use_cors: bool
        if ``True`` (the default), then CORS is enabled on this proxy

    To register a new proxy, use the ``register_http_proxy`` method with an instance of a HTTPProxy class

    Example:
    ::
        from superdesk.flask import Flask
        from superdesk.http_proxy import HTTPProxy, register_http_proxy

        def init_app(app: Flask) -> None:
            register_http_proxy(
                app,
                HTTPProxy(
                    endpoint_name="belga.ai_proxy",
                    internal_url="belga/ai",
                    external_url="http://localhost:5001",
                )
            )

    Note: The ``internal_url`` is prefixed with the ``URL_PREFIX`` config (defaults to ``api``).

    Example Requests:
    ::
        http://localhost:5000/api/belga/ai                 -> http://localhost:5001
        http://localhost:5000/api/belga/ai/articles/123456 -> http://localhost:5001/articles/123456
        url_for("belga.ai_proxy")                          -> /api/belga/ai
        url_for("belga.ai_proxy", _external=True)          -> http://localhost:5000/api/belga/ai
    """

    endpoint_name: str
    internal_url: str
    external_url: str
    http_methods: List[str]
    auth: bool
    use_cors: bool
    session: requests.Session

    def __init__(
        self,
        endpoint_name: str,
        internal_url: str,
        external_url: str,
        http_methods: Optional[List[str]] = None,
        auth: bool = True,
        use_cors: bool = True,
    ):
        self.endpoint_name = endpoint_name
        self.internal_url = internal_url.lstrip("/").rstrip("/")
        self.external_url = external_url
        self.http_methods = http_methods or ["OPTIONS", "GET", "POST", "PATCH", "PUT", "DELETE"]
        self.auth = auth
        self.use_cors = use_cors
        self.session = requests.Session()

    def get_internal_url(self) -> str:
        """Returns the base URL route used when registering the proxy with Flask"""

        url_prefix = cast(str, get_app_config("URL_PREFIX")).lstrip("/")
        return f"/{url_prefix}/{self.internal_url}"

    async def process_request(self, path: str) -> ResponseTypes:
        """The main function used for processing requests from the client"""

        self.authenticate()
        response = await (make_response() if request.method == "OPTIONS" else self.send_proxy_request())
        if self.use_cors:
            # Ignore following type check, as ``typing--Werkzeug=1.0.9`` is missing stub for ``update`` method
            response.headers.set("Access-Control-Allow-Origin", "*")

            response.headers.update(get_cors_headers(",".join(self.http_methods)))  # type: ignore
        return response

    def authenticate(self):
        """If auth is enabled, make sure the current session is authenticated"""

        # Use ``_blueprint`` for resource name for auth purposes (copied from the ``blueprint_auth`` decorator)
        current_app = get_current_app()

        if self.auth and not current_app.auth.authorized([], "_blueprint", request.method):
            # Calling ``auth.authenticate`` raises a ``SuperdeskApiError.unauthorizedError()`` exception
            current_app.auth.authenticate()

    async def send_proxy_request(self) -> ResponseTypes:
        result = self.session.request(**(await self.get_proxy_request_kwargs()))
        return self.construct_response(result)

    async def get_proxy_request_kwargs(self) -> Dict[str, Any]:
        """Returns the kwargs used when executing the ``requests.request`` call to the external service"""

        proxied_path = request.full_path.replace(self.get_internal_url(), "")
        if proxied_path == "?":
            proxied_url = self.external_url
        elif proxied_path.startswith("/"):
            proxied_url = self.external_url.rstrip("/") + "/" + proxied_path.lstrip("/")
        else:
            proxied_url = self.external_url + proxied_path

        headers = {
            k: v for k, v in request.headers if k.lower() not in ("host", "authorization", "cookie")
        }  # exclude "host" & "authorization" headers
        headers["User-Agent"] = f"Superdesk-{superdesk_version}"

        return dict(
            url=proxied_url,
            method=request.method,
            headers=headers,
            data=await request.get_data(),
            allow_redirects=True,
            stream=True,
            timeout=get_app_config("HTTP_PROXY_TIMEOUT"),
        )

    def construct_response(self, result: requests.Response) -> ResponseTypes:
        """Returns the Flask.Response instance based on the response from the external service"""

        # Exclude "Hop-by-hop" headers
        # (see RFC 2616 section 13.5.1 ref. https://www.rfc-editor.org/rfc/rfc2616#section-13.5.1)
        excluded_headers = [
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        ]
        headers = [(k, v) for k, v in result.raw.headers.items() if k.lower() not in excluded_headers]

        return get_current_app().response_class(
            result.iter_content(),
            result.status_code,
            headers,
            content_type=result.headers.get("Content-Type"),
        )


def register_http_proxy(app: Flask, proxy: HTTPProxy):
    """Register a HTTPProxy instance by adding URL rules to Flask"""

    internal_url = proxy.get_internal_url()
    app.add_url_rule(
        internal_url, proxy.endpoint_name, proxy.process_request, defaults={"path": ""}, methods=proxy.http_methods
    )
    app.add_url_rule(
        f"{internal_url}/<path:path>", proxy.endpoint_name, proxy.process_request, methods=proxy.http_methods
    )
