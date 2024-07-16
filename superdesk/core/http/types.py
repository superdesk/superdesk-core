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
    Any,
    Protocol,
    Sequence,
    Optional,
    Callable,
    Awaitable,
    Literal,
    List,
    TypeVar,
    Mapping,
    Union,
    TypedDict,
    Dict,
)
from inspect import signature

from dataclasses import dataclass
from pydantic import BaseModel

HTTP_METHOD = Literal["GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"]
PydanticModelType = TypeVar("PydanticModelType", bound=BaseModel)


@dataclass
class HTTPResponse:
    """Dataclass for endpoints to return response from a request"""

    #: The body of the response (Flask will determine data type for us)
    body: Any

    #: HTTP Status Code of the response
    status_code: int

    #: Any additional headers to be added
    headers: Sequence


#: Function for use with a HTTPEndpoint registration and request processing
#:
#: Supported endpoint signatures::
#:
#:      # Request Only
#:      async def test1(request: HTTPRequest) -> HTTPResponse
#:
#:      # Args and Request
#:      async def test2(
#:          args: Pydantic.BaseModel,
#:          params: None,
#:          request: HTTPRequest
#:      ) -> HTTPResponse
#:
#:      # Params and Request
#:      async def test3(
#:          args: None,
#:          params: Pydantic.BaseModel,
#:          request: HTTPRequest
#:      ) -> HTTPResponse
#:
#:      # Args, Params and Request
#:      async def test4(
#:          args: Pydantic.BaseModel,
#:          params: Pydantic.BaseModel,
#:          request: HTTPRequest
#:      ) -> HTTPResponse
HTTPEndpointFunction = Union[
    Callable[
        ["HTTPRequest"],
        Awaitable[HTTPResponse],
    ],
    Callable[
        [PydanticModelType, PydanticModelType, "HTTPRequest"],
        Awaitable[HTTPResponse],
    ],
    Callable[
        [None, PydanticModelType, "HTTPRequest"],
        Awaitable[HTTPResponse],
    ],
    Callable[
        [PydanticModelType, None, "HTTPRequest"],
        Awaitable[HTTPResponse],
    ],
    Callable[
        [None, None, "HTTPRequest"],
        Awaitable[HTTPResponse],
    ],
]


class HTTPEndpoint:
    """Base class used for registering and processing endpoints"""

    #: URL for the endpoint
    url: str

    #: Name of the endpoint (must be unique)
    name: str

    #: HTTP Methods allowed for this endpoint
    methods: List[HTTP_METHOD]

    #: The callback function used to process the request
    func: HTTPEndpointFunction

    def __init__(
        self,
        url: str,
        func: HTTPEndpointFunction,
        methods: Optional[List[HTTP_METHOD]] = None,
        name: Optional[str] = None,
    ):
        self.url = url
        self.func = func
        self.methods = methods or ["GET"]
        self.name = name or func.__name__

    def __call__(self, args: Dict[str, Any], params: Dict[str, Any], request: "HTTPRequest"):
        func_params = signature(self.func).parameters
        if "args" not in func_params and "params" not in func_params:
            return self.func(request)  # type: ignore[call-arg,arg-type]

        arg_type = func_params["args"] if "args" in func_params else None
        request_args = None
        if arg_type is not None and arg_type.annotation is not None and issubclass(arg_type.annotation, BaseModel):
            request_args = arg_type.annotation.model_validate(args)

        param_type = func_params["params"] if "params" in func_params else None
        url_params = None
        if (
            param_type is not None
            and param_type.annotation is not None
            and issubclass(param_type.annotation, BaseModel)
        ):
            url_params = param_type.annotation.model_validate(params)

        return self.func(request_args, url_params, request)  # type: ignore[call-arg,arg-type]


class HTTPRequest(Protocol):
    """Protocol to define common request functionality

    This is implemented in `SuperdeskEve` app using Flask to provide the required functionality.
    """

    #: The current HTTPEndpoint being processed
    endpoint: HTTPEndpoint

    @property
    def method(self) -> HTTP_METHOD:
        """Returns the current HTTP method for the request"""
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


class HTTPEndpointGroup:
    """Base class used for registering a group of endpoints"""

    #: Optional url prefix to be added to all routes of this group
    url_prefix: Optional[str]

    #: List of endpoints registered with this group
    endpoints: List[HTTPEndpoint]

    def __init__(self, url_prefix: Optional[str] = None):
        self.url_prefix = url_prefix
        self.endpoints = []

    def endpoint(
        self,
        url: str,
        name: Optional[str] = None,
        methods: Optional[List[HTTP_METHOD]] = None,
    ):
        """Decorator function to register an endpoint to this group

        :param url: The URL of the endpoint
        :param name: The optional name of the endpoint
        :param methods: The optional list of HTTP methods allowed
        """

        def fdec(func: HTTPEndpointFunction):
            self.endpoints.append(
                HTTPEndpoint(
                    f"{self.url_prefix}/{url}" if self.url_prefix else url,
                    func,
                    methods=methods,
                    name=name,
                )
            )

        return fdec


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
    _items: List[Dict[str, Any]]

    #: HATEOAS links
    _links: Dict[str, Any]

    #: Response metadata
    _meta: RestResponseMeta


def http_endpoint(url: str, name: Optional[str] = None, methods: Optional[List[HTTP_METHOD]] = None):
    """Decorator function to convert a pure function to a HTTPEndpoint instance

    This is then later used to register with a Module or the app.

    :param url: The URL of the endpoint
    :param name: The optional name of the endpoint
    :param methods: The optional list of HTTP methods allowed
    """

    def convert_to_endpoint(func: HTTPEndpointFunction):
        return HTTPEndpoint(
            url=url,
            name=name,
            methods=methods,
            func=func,
        )

    return convert_to_endpoint
