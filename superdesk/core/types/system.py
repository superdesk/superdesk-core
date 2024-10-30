from typing import Any, Sequence, Protocol

from .web import Request, Endpoint, EndpointGroup


class NotificationClientProtocol(Protocol):
    open: bool
    messages: Sequence[str]

    def close(self) -> None:
        ...

    def send(self, message: str) -> None:
        ...

    def reset(self) -> None:
        ...


class WSGIApp(Protocol):
    """Protocol for defining functionality from a WSGI application (such as Eve/Flask)

    A class instance that adheres to this protocol is passed into the SuperdeskAsyncApp constructor.
    This way the SuperdeskAsyncApp does not need to know the underlying WSGI application, just that
    it provides certain functionality.
    """

    #: Config for the application
    config: dict[str, Any]

    #: Config for the front-end application
    client_config: dict[str, Any]

    testing: bool = False

    #: Interface to upload/download/query media
    media: Any

    mail: Any

    data: Any

    storage: Any

    auth: Any

    subjects: Any

    notification_client: NotificationClientProtocol

    locators: Any

    celery: Any

    redis: Any

    jinja_loader: Any

    jinja_env: Any

    extensions: dict[str, Any]

    def register_endpoint(self, endpoint: Endpoint | EndpointGroup):
        ...

    def register_resource(self, name: str, settings: dict[str, Any]):
        ...

    def upload_url(self, media_id: str) -> str:
        ...

    def download_url(self, media_id: str) -> str:
        ...

    # TODO: Provide proper type here, context manager
    def app_context(self):
        ...

    def get_current_user_dict(self) -> dict[str, Any] | None:
        ...

    def response_class(self, *args, **kwargs) -> Any:
        ...

    def validator(self, *args, **kwargs) -> Any:
        ...

    def init_indexes(self, ignore_duplicate_keys: bool = False) -> None:
        ...

    def as_any(self) -> Any:
        ...

    def get_current_request(self) -> Request | None:
        ...

    def get_endpoint_for_current_request(self) -> Endpoint | None:
        ...
