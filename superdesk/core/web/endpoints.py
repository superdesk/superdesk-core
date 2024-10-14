# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any, Awaitable
from inspect import signature, isawaitable
import logging

from pydantic import BaseModel, ValidationError

from superdesk.core.types import (
    Request,
    Response,
    EndpointFunction,
    HTTP_METHOD,
    Endpoint as EndpointProtocol,
    AuthConfig,
    EndpointGroup as EndpointGroupProtocol,
)


logger = logging.getLogger(__name__)


class Endpoint(EndpointProtocol):
    """Base class used for registering and processing endpoints"""

    async def __call__(self, args: dict[str, Any], params: dict[str, Any], request: Request):
        from superdesk.core.resources import ResourceModel
        from superdesk.core import get_current_async_app

        # Implement Auth here
        if request.endpoint.get_auth_rules() is not False:
            async_app = get_current_async_app()
            response = await async_app.auth.authenticate(request)
            if response is not None:
                logger.warning("Authenticate returned a non-None value")
                return response
            response = await async_app.auth.authorize(request)
            if response is not None:
                logger.warning("Authorize returned a non-None value")
                return response

        response = self._run_endpoint_func(args, params, request)
        if isawaitable(response):
            response = await response

        if not isinstance(response, Response):
            # TODO-ASYNC: Implement our own wrapper around Response for specific use cases
            # like redirect or abort and handle these here
            # We may have received a different response, such as a flask redirect call
            # So we return it here
            return response
        elif isinstance(response.body, ResourceModel):
            response.body = response.body.to_dict()

        return response

    def _run_endpoint_func(
        self, args: dict[str, Any], params: dict[str, Any], request: Request
    ) -> Awaitable[Response] | Response:
        func_params = signature(self.func).parameters
        if not len(func_params):
            return self.func()  # type: ignore[call-arg,arg-type]
        elif "args" not in func_params and "params" not in func_params:
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
            try:
                url_params = param_type.annotation.model_validate(params)
            except ValidationError as error:
                from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error

                errors = {
                    field: list(err.values())[0]
                    for field, err in get_field_errors_from_pydantic_validation_error(error).items()
                }
                return Response(errors, 400, ())

        return self.func(request_args, url_params, request)  # type: ignore[call-arg,arg-type]


def return_404() -> Response:
    return Response("", 404)


class NullEndpointClass(Endpoint):
    def __init__(self):
        super().__init__(url="<null>", func=return_404)


NullEndpoint = NullEndpointClass()


class EndpointGroup(EndpointGroupProtocol):
    """Base class used for registering a group of endpoints"""

    def __init__(
        self,
        name: str,
        import_name: str,
        url_prefix: str | None = None,
        auth: AuthConfig = None,
    ):
        super().__init__(
            url="",
            func=return_404,
            auth=auth,
        )
        self.name = name
        self.import_name = import_name
        self.url_prefix = url_prefix
        self.endpoints = []

    def endpoint(
        self,
        url: str,
        name: str | None = None,
        methods: list[HTTP_METHOD] | None = None,
        auth: AuthConfig = None,
    ):
        """Decorator function to register an endpoint to this group

        :param url: The URL of the endpoint
        :param name: The optional name of the endpoint
        :param methods: The optional list of HTTP methods allowed
        """

        def fdec(func: EndpointFunction):
            endpoint_func = Endpoint(
                f"{self.url}/{url}" if self.url else url,
                func,
                methods=methods,
                name=name,
                auth=auth,
                parent=self,
            )
            self.endpoints.append(endpoint_func)
            return endpoint_func

        return fdec

    def __call__(self, args: dict[str, Any], params: dict[str, Any], request: Request):
        return return_404()


def endpoint(url: str, name: str | None = None, methods: list[HTTP_METHOD] | None = None, auth: AuthConfig = None):
    """Decorator function to convert a pure function to an Endpoint instance

    This is then later used to register with a Module or the app.

    :param url: The URL of the endpoint
    :param name: The optional name of the endpoint
    :param methods: The optional list of HTTP methods allowed
    """

    def convert_to_endpoint(func: EndpointFunction):
        return Endpoint(
            url=url,
            name=name,
            methods=methods,
            func=func,
            auth=auth,
        )

    return convert_to_endpoint
