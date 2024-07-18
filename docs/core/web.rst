.. core_http:

Web Server
==========

.. module:: superdesk.core.web

In Superdesk v3.0+ we use an abstraction layer when it comes to the web server functionality. This means that
we don't directly interact with the Flask library, but Superdesk specific classes and functionality instead.

For example::

    from superdesk.core.module import Module
    from superdesk.core.web import (
        endpoint,
        Request,
        Response,
    )

    @endpoint("hello/world", methods=["GET"])
    async def hello_world(request: Request) -> Response:
        return Response(
            body="hello, world!",
            status_code=200,
            headers=()
        )

    module = Module(
        name="tests.http",
        endpoints=[hello_world]
    )


Declaring Endpoints
-------------------

There are three ways to declare a function as an HTTP endpoint.

1. Using the :func:`endpoint <types.endpoint>` decorator::

    from superdesk.core.web import (
        Request,
        Response,
        endpoint,
    )

    @endpoint("hello/world", methods=["GET"])
    async def hello_world(request: Request) -> Response:
        ...

2. Using the :class:`Endpoint <types.Endpoint>` class::

    from superdesk.core.web import (
        Request,
        Response,
        Endpoint,
    )

    async def hello_world(request: Request) -> Response:
        ...

    endpoint = Endpoint(
        url="hello/world",
        methods=["GET"],
        func=hello_world
    )

3. Using the :class:`EndpointGroup <types.EndpointGroup>` class group::

    from superdesk.core.web import (
        Request,
        Response,
        EndpointGroup,
    )

    group = EndpointGroup(url_prefix="hello)

    @group.endpoint(url="world", methods=["GET"])
    async def hello_world(request: Request) -> Response:
        ...

Registering Endpoints:
----------------------

There are two ways to register an endpoint with the system.

1. Manually using the :attr:`WSGIApp.register_endpoint <types.WSGIApp.register_endpoint>` function::

    from superdesk.core.app import SuperdeskAsyncApp

    def init(app: SuperdeskAsyncApp):
        app.wsgi.register_endpoint(hello_world)

2. Automatically with the :attr:`endpoints <superdesk.core.module.Module.endpoints>` module config::

    from superdesk.core.module import Module

    module = Module(
        name="my.module",
        endpoints=[hello_world, group]
    )

Resource REST Endpoints
-----------------------

REST endpoints can be enabled for a resource by defining the
:attr:`rest_endpoints <superdesk.core.resources.model.ResourceConfig.rest_endpoints>` attribute on the ResourceConfig.
See :class:`RestEndpointConfig <superdesk.core.resources.resource_rest_endpoints.RestEndpointConfig>` for config
options.

For example::

    from superdesk.core.module import Module
    from superdesk.core.resources import (
        ResourceConfig,
        ResourceModel,
        RestEndpointConfig,
    )

    # Define your resource model and config
    class User(ResourceModel):
        first_name: str
        last_name: str

    # Configure the resource
    user_resource_config = ResourceConfig(
        name="users",
        data_class=User,

        # Including the `rest_endpoints` config
        rest_endpoints=RestEndpointConfig(),
    )

    module = Module(name="tests.users")


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

    @endpoint(
        "users_async/<string:user_id>/action/<string:action>",
        methods=["GET"]
    )
    async def hello_world(
        args: RouteArguments,
        params: URLParams,
        request: Request,
    ) -> Response:
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

        return Response(
            "hello, world!",
            200,
            ()
        )

    def init(app: SuperdeskAsyncApp) -> None:
        app.wsgi.register_endpoint(hello_world)

API References
--------------

.. autoclass:: superdesk.core.web.types.Response
    :member-order: bysource
    :members:
    :undoc-members:

.. autodata:: superdesk.core.web.types.EndpointFunction

.. autoclass:: superdesk.core.web.types.Endpoint
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.web.types.Request
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.web.types.EndpointGroup
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.web.types.RestResponseMeta
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.web.types.RestGetResponse
    :member-order: bysource
    :members:
    :undoc-members:

.. autofunction:: superdesk.core.web.types.endpoint

.. autoclass:: superdesk.core.web.rest_endpoints.RestEndpoints
    :member-order: bysource
    :members:
    :undoc-members:


.. autoclass:: superdesk.core.resources.resource_rest_endpoints.RestEndpointConfig
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.resources.resource_rest_endpoints.ResourceRestEndpoints
    :member-order: bysource
    :members:
    :undoc-members:

.. autoclass:: superdesk.core.web.types.WSGIApp
    :member-order: bysource
    :members:
    :undoc-members:
