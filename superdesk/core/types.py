# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import (
    Dict,
    Any,
    Optional,
    List,
    Literal,
    Sequence,
    Union,
    Callable,
    Awaitable,
    TypeVar,
    Protocol,
    Mapping,
    NoReturn,
)
from typing_extensions import TypedDict
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, NonNegativeInt, field_validator

DefaultNoValue = object()


HTTP_METHOD = Literal["GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"]


#: The data type for projections, either a list of field names, or a dictionary containing
#: the field and enable/disable state
ProjectedFieldArg = (
    list[str] | dict[str, Literal[0]] | dict[str, Literal[1]] | dict[str, Literal[True]] | dict[str, Literal[False]]
)

#: Type used to provide list of sort params to be used
SortListParam = list[tuple[str, Literal[1, -1]]]

#: Type used for sort param in service requests
#: can be a string, which will convert to an :attr:`SortListParam` type
SortParam = str | SortListParam

#: Type used for version param in service requests
#: Can be either ``"all"`` or an int ``>= 0``
VersionParam = Literal["all"] | NonNegativeInt


class SearchArgs(TypedDict, total=False):
    """Dictionary containing Elasticsearch search arguments

    This is for use with the `.find` methods in elastic clients
    """

    #: A JSON string containing an elasticsearch query
    source: str

    #: A query string
    q: str

    #: Default field, for use with the query string
    df: str

    #: Default operator, for use with the query string (defaults to "AND")
    default_operator: str

    #: A JSON string containing bool query filters, to be applied to the elastic query
    filter: str

    #: A list of dictionaries containing bool query filters, to be applied to the elastic query
    filters: List[Dict[str, Any]]

    #: A JSON string containing the field projections to filter out the returned fields
    projections: str

    version: VersionParam | None


class SearchRequest(BaseModel):
    """Dataclass containing Elasticsearch request arguments"""

    model_config = ConfigDict(extra="allow")

    #: Argument for the search filters
    args: Optional[SearchArgs] = None

    #: Sorting to be used
    sort: SortParam | None = None

    #: Maximum number of documents to be returned
    max_results: int = 25

    #: The page number to be returned
    page: int = 1

    #: A JSON string contianing an Elasticsearch where query
    where: str | dict | None = None

    #: If `True`, will include aggregations with the result
    aggregations: bool = False

    #: If `True`, will include highlights with the result
    highlight: bool = False

    #: The field projections to be applied
    projection: Optional[ProjectedFieldArg] = None

    @field_validator("projection", mode="before")
    def parse_projection(cls, value: ProjectedFieldArg | str | None) -> ProjectedFieldArg | None:
        from superdesk.core import json

        if not value:
            return None
        elif isinstance(value, str):
            return json.loads(value)
        return value


@dataclass
class Response:
    """Dataclass for endpoints to return response from a request"""

    #: The body of the response (Flask will determine data type for us)
    body: Any

    #: HTTP Status Code of the response
    status_code: int = 200

    #: Any additional headers to be added
    headers: Sequence = ()


PydanticModelType = TypeVar("PydanticModelType", bound=BaseModel)


#: Function for use with a Endpoint registration and request processing
#:
#: Supported endpoint signatures::
#:
#:      # Response only
#:      async def test() -> Response:
#:
#:      # Request Only
#:      async def test1(request: Request) -> Response
#:
#:      # Args and Request
#:      async def test2(
#:          args: Pydantic.BaseModel,
#:          params: None,
#:          request: Request
#:      ) -> Response
#:
#:      # Params and Request
#:      async def test3(
#:          args: None,
#:          params: Pydantic.BaseModel,
#:          request: Request
#:      ) -> Response
#:
#:      # Args, Params and Request
#:      async def test4(
#:          args: Pydantic.BaseModel,
#:          params: Pydantic.BaseModel,
#:          request: Request
#:      ) -> Response
EndpointFunction = Union[
    Callable[
        [],
        Awaitable[Response],
    ],
    Callable[
        ["Request"],
        Awaitable[Response],
    ],
    Callable[
        [PydanticModelType, PydanticModelType, "Request"],
        Awaitable[Response],
    ],
    Callable[
        [None, PydanticModelType, "Request"],
        Awaitable[Response],
    ],
    Callable[
        [PydanticModelType, None, "Request"],
        Awaitable[Response],
    ],
    Callable[
        [None, None, "Request"],
        Awaitable[Response],
    ],
    Callable[
        [],
        Response,
    ],
    Callable[
        ["Request"],
        Response,
    ],
    Callable[
        [PydanticModelType, PydanticModelType, "Request"],
        Response,
    ],
    Callable[
        [None, PydanticModelType, "Request"],
        Response,
    ],
    Callable[
        [PydanticModelType, None, "Request"],
        Response,
    ],
    Callable[
        [None, None, "Request"],
        Response,
    ],
]


class RequestStorageProvider(Protocol):
    def get(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def pop(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        ...


class RequestSessionStorageProvider(RequestStorageProvider):
    def set_session_permanent(self, value: bool) -> None:
        ...

    def is_session_permanent(self) -> bool:
        return False

    def clear(self) -> None:
        ...


class RequestStorage(Protocol):
    session: RequestSessionStorageProvider
    request: RequestStorageProvider


class Request(Protocol):
    """Protocol to define common request functionality

    This is implemented in `SuperdeskEve` app using Flask to provide the required functionality.
    """

    #: The current Endpoint being processed
    endpoint: "Endpoint"
    storage: RequestStorage
    user: Any | None

    @property
    def method(self) -> HTTP_METHOD:
        """Returns the current HTTP method for the request"""
        ...

    @property
    def url(self) -> str:
        """Returns the URL of the current request"""
        ...

    @property
    def path(self) -> str:
        """Returns the URL of the current request"""
        ...

    def get_header(self, key: str) -> Optional[str]:
        """Get an HTTP header from the current request"""
        ...

    async def get_json(self) -> Union[Any, None]:
        """Get the body of the current request in JSON format"""
        ...

    async def get_form(self) -> Mapping:
        """Get the body of the current request in form format"""
        ...

    async def get_data(self) -> Union[bytes, str]:
        """Get the body of the current request in raw bytes format"""
        ...

    async def abort(self, code: int, *args: Any, **kwargs: Any) -> NoReturn:
        ...

    def get_view_args(self, key: str) -> str | None:
        ...

    def get_url_arg(self, key: str) -> str | None:
        ...

    def redirect(self, location: str, code: int = 302) -> Any:
        ...


AuthRule = Callable[[Request], Awaitable[Any | None]]
AuthConfig = Literal[False] | list[AuthRule] | dict[str, AuthRule] | None


class Endpoint:
    """Base class used for registering and processing endpoints"""

    #: URL for the endpoint
    url: str

    #: Name of the endpoint (must be unique)
    name: str

    #: HTTP Methods allowed for this endpoint
    methods: List[HTTP_METHOD]

    #: The callback function used to process the request
    func: EndpointFunction

    auth: AuthConfig

    def __init__(
        self,
        url: str,
        func: EndpointFunction,
        methods: list[HTTP_METHOD] | None = None,
        name: str | None = None,
        auth: AuthConfig = None,
        parent: Union["EndpointGroup", None] = None,
    ):
        self.url = url
        self.func = func
        self.methods = methods or ["GET"]
        self.name = name or func.__name__
        self.auth = auth
        self.parent = parent

    async def __call__(self, args: dict[str, Any], params: dict[str, Any], request: Request):
        ...

    def get_auth_rules(self) -> AuthConfig:
        if self.auth is None:
            return self.parent.get_auth_rules() if self.parent is not None else None
        return self.auth


class EndpointGroup(Endpoint):
    """Base class used for registering a group of endpoints"""

    # #: Name for this endpoint group. Will be prepended to each endpoint name
    # name: str

    #: The import name of the module where this object is defined.
    #: Usually :attr:`__name__` should be used.
    import_name: str

    #: Optional url prefix to be added to all routes of this group
    url_prefix: Optional[str]

    #: List of endpoints registered with this group
    endpoints: List[Endpoint]

    def endpoint(
        self,
        url: str,
        name: str | None = None,
        methods: list[HTTP_METHOD] | None = None,
        auth: AuthConfig = None,
    ):
        ...


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

    extensions: Dict[str, Any]

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


class RestResponseMeta(TypedDict):
    """Dictionary to hold the response metadata for a REST request"""

    #: Current page requested
    page: int

    #: Maximum results requested
    max_results: int

    #: Total number of documents found
    total: int


class RestGetResponse(TypedDict, total=False):
    """Dictionary to hold the response for a REST request"""

    #: The list of documents found for the search request
    _items: list[dict[str, Any]]

    #: HATEOAS links
    _links: dict[str, Any]

    #: Response metadata
    _meta: RestResponseMeta
