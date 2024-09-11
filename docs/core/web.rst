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

    group = EndpointGroup(
        name="tests",
        import_name=__name__,
        url_prefix="hello"
    )

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

    module = Module(
        name="tests.users",
        resources=[user_resource_config],
    )


Resource REST Endpoint with Parent
----------------------------------

REST endpoints can also include a parent/child relationship with the resource. This is achieved using the
:class:`RestParentLink <superdesk.core.resources.resource_rest_endpoints.RestParentLink>`
attribute on the RestEndpointConfig.

Example config::

    from typing import Annotated
    from superdesk.core.module import Module
    from superdesk.core.resources import (
        ResourceConfig,
        ResourceModel,
        RestEndpointConfig,
        RestParentLink,
    )
    from superdesk.core.resources.validators import (
        validate_data_relation_async,
    )

    # 1. Define parent resource and config
    class Company(ResourceModel):
        name: str

    company_resource_config = ResourceConfig(
        name="companies",
        data_class=Company,
        rest_endpoints=RestEndpointConfig()
    )

    # 2. Define child resource and config
    class User(ResourceModel):
        first_name: str
        last_name: str

        # 2a. Include a field that references the parent
        company: Annotated[
            str,
            validate_data_relation_async(
                company_resource_config.name,
            ),
        ]

    user_resource_config = ResourceConfig(
        name="users",
        data_class=User,
        rest_endpoints=RestEndpointConfig(

            # 2b. Include a link to Company as a parent resource
            parent_links=[
                RestParentLink(
                    resource_name=company_resource_config.name,
                    model_id_field="company",
                ),
            ],
        ),
    )

    # 3. Register the resources with a module
    module = Module(
        name="tests.users",
        resources=[
            company_resource_config,
            user_resource_config,
        ],
    )


The above example exposes the following URLs:

* /api/companies
* /api/companies/``<item_id>``
* /api/companies/``<company>``/users
* /api/companies/``<company>``/users/``<item_id>``

As you can see the ``users`` endpoints are prefixed with ``/api/company/<company>/``.

This provides the following functionality:

* Validation that a Company must exist for the user
* Populates the ``company`` field of a User with the ID from the URL
* When searching for users, will only provide users for the specific company provided in the URL of the request

For example::

    async def test_users():
        # Create the parent Company
        response = await client.post(
            "/api/company",
            json={"name": "Sourcefabric"}
        )

        # Retrieve the Company ID from the response
        company_id = (await response.get_json())[0]

        # Attemps to create a user with non-existing company
        # responds with a 404 - NotFound error
        response = await client.post(
            f"/api/company/blah_blah/users",
            json={"first_name": "Monkey", "last_name": "Mania"}
        )
        assert response.status_code == 404

        # Create the new User
        # Notice the ``company_id`` is used in the URL
        response = await client.post(
            f"/api/company/{company_id}/users",
            json={"first_name": "Monkey", "last_name": "Mania"}
        )
        user_id = (await response.get_json())[0]

        # Retrieve the new user
        response = await client.get(
            f"/api/company/{company_id}/users/{user_id}"
        )
        user_dict = await response.get_json()
        assert user_dict["company"] == company_id

        # Retrieve all company users
        response = await client.get(
            f"/api/company/{company_id}/users"
        )
        users_dict = (await response.get_json())["_items"]
        assert len(users_dict) == 1
        assert users_dict[0]["_id"] == user_id


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

.. autoclass:: superdesk.core.resources.resource_rest_endpoints.RestParentLink
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
