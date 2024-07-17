.. core_http:

Web Server
==========

.. module:: superdesk.core.http

In Superdesk v3.0+ we use an abstraction layer when it comes to the web server functionality. This means that
we don't directly interact with the Flask library, but Superdesk specific classes and functionality instead.

For example::

    from superdesk.core.module import Module
    from superdesk.core.http.types import (
        http_endpoint,
        HTTPRequest,
        HTTPResponse,
    )

    @http_endpoint("hello/world", methods=["GET"])
    async def hello_world(request: HTTPRequest) -> HTTPResponse:
        return HTTPResponse(
            body="hello, world!",
            status_code=200,
            headers=()
        )

    module = Module(
        name="tests.http",
        http_endpoints=[hello_world]
    )


Declaring Endpoints
-------------------

There are three ways to declare a function as an HTTP endpoint.

1. Using the :func:`http_endpoint <types.http_endpoint>` decorator::

    from superdesk.core.http.types import (
        HTTPRequest,
        HTTPResponse,
        http_endpoint,
    )

    @http_endpoint("hello/world", methods=["GET"])
    async def hello_world(request: HTTPRequest) -> HTTPResponse:
        ...
2. Using the :class:`HTTPEndpoint <types.HTTPEndpoint>` class::

    from superdesk.core.http.types import (
        HTTPRequest,
        HTTPResponse,
        HTTPEndpoint,
    )

    async def hello_world(request: HTTPRequest) -> HTTPResponse:
        ...

    endpoint = HTTPEndpoint(
        url="hello/world",
        methods=["GET"],
        func=hello_world
    )

3. Using the :class:`HTTPEndpointGroup <types.HTTPEndpointGroup>` class group::

    from superdesk.core.http.types import (
        HTTPRequest,
        HTTPResponse,
        HTTPEndpointGroup,
    )

    group = HTTPEndpointGroup(url_prefix="hello)

    @group.endpoint(url="world", methods=["GET"])
    async def hello_world(request: HTTPRequest) -> HTTPResponse:
        ...

Registering Endpoints:
----------------------

There are three ways to register an endpoint with the system.

1. Manually using the :attr:`WSGIApp.register_endpoint <wsgi.WSGIApp.register_endpoint>` function::

    from superdesk.core.app import SuperdeskAsyncApp

    def init(app: SuperdeskAsyncApp):
        app.wsgi.register_endpoint(hello_world)

2. Manually using the :attr:`WSGIApp.register_endpoint_group <wsgi.WSGIApp.register_endpoint_group>` function::

    from superdesk.core.app import SuperdeskAsyncApp

    def init(app: SuperdeskAsyncApp):
        app.wsgi.register_endpoint_group(group)

3. Automatically with the :attr:`http_endpoints <superdesk.core.module.Module.http_endpoints>` module config::

    from superdesk.core.module import Module

    module = Module(
        name="my.module",
        http_endpoints=[hello_world, group]
    )

Resource REST Endpoints
-----------------------

There is a special endpoint group type, the :class:`ResourceEndpoints <resource_endpoints.ResourceEndpoints>` class,
that creates a REST endpoint for us based on a registered resource. This will automatically
create, declare, register and process the endpoints for us.

All it requires to be used is to create an instance of the group type, providing the
:class:`ResourceConfig <superdesk.core.resources.model.ResourceConfig>` for the desired resource, then
register the group like any other HTTPEndpointGroup.

For example::

    from superdesk.core.module import Module
    from superdesk.core.resources import (
        ResourceConfig,
        ResourceModel,
    )
    from superdesk.core.http.resource_endpoints import (
        ResourceEndpoints,
    )

    # Define your resource model and config
    class User(ResourceModel):
        first_name: str
        last_name: str

    user_resource_config = ResourceConfig(
        name="users",
        data_class=User,
    )

    # Create an instance of ResourceEndpoints
    # passing in the resource config
    user_rest_endpoints = ResourceEndpoints(user_resource_config)

    module = Module(
        name="tests.users",

        # And register the endpoint group like any other
        http_endpoints=[user_rest_endpoints]
    )


Validation
----------

Request route arguments and URL params can be validated against Pydantic models. All you need to do is to define
the model for each argument type, and the system will validate them when processing the request.
If the request does not pass validation, a Pydantic ValidationError will be raised.

For example::

    from typing import Optional
    from enum import Enum
    from pydantic import BaseModel

    class UserActions(str, Enum):
        activate = "activate"
        disable = "disable"

    class RouteArguments(BaseModel):
        user_id: str
        action: UserActions

    class URLParams(BaseModel):
        verbose: bool = False

    @http_endpoint(
        "users_async/<string:user_id>/action/<string:action>",
        methods=["GET"]
    )
    async def hello_world(
        args: RouteArguments,
        params: URLParams,
        request: HTTPRequest,
    ) -> HTTPResponse:
        # If the request reaches this line,
        # we have valid arguments & params
        user = get_user(args.user_id)
        if args.action == UserActions.activate:
            pass
        elif args.action == UserActions.disable:
            pass
        else:
            # This line should never be reached,
            # as validation would have caught this already
            assert False, "unreachable"

        return HTTPResponse(
            "hello, world!",
            200,
            ()
        )

    def init(app: SuperdeskAsyncApp) -> None:
        app.wsgi.register_endpoint(hello_world)

API References
--------------

.. autoclass:: superdesk.core.http.types.HTTPResponse
    :member-order: bysource
    :members:
    :undoc-members:

.. autodata:: superdesk.core.http.types.HTTPEndpointFunction

.. autoclass:: superdesk.core.http.types.HTTPEndpoint
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.http.types.HTTPRequest
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.http.types.HTTPEndpointGroup
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.http.types.RestResponseMeta
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.http.types.RestGetResponse
    :member-order: bysource
    :members:
    :undoc-members:

.. autofunction:: superdesk.core.http.types.http_endpoint

.. autoclass:: superdesk.core.http.resource_endpoints.ResourceEndpoints
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.http.wsgi.WSGIApp
    :member-order: bysource
    :members:
    :undoc-members:
