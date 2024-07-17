# mypy: disable-error-code="override, attr-defined"
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any, AnyStr

from urllib.request import Request as U2Request
from asgiref.wsgi import WsgiToAsgi
from werkzeug.datastructures import Headers, Authorization
from flask import Flask
from quart import Response
from quart.datastructures import FileStorage
from quart.testing import QuartClient
from quart.testing.utils import make_test_headers_path_and_query_string, make_test_body_with_headers, make_test_scope
from quart.testing.client import _TestCookieJarResponse

from superdesk.core.resources.model import ResourceModel


class AsyncTestClient(QuartClient):
    def __init__(self, app: Flask, asgi_app: WsgiToAsgi) -> None:
        setattr(asgi_app, "config", app.config)
        setattr(asgi_app, "response_class", Response)
        super().__init__(asgi_app)  # type: ignore

    def model_instance_to_json(self, model_instance: ResourceModel):
        return model_instance.model_dump(by_alias=True, exclude_unset=True, mode="json")

    async def post(self, *args, **kwargs) -> Response:
        if "json" in kwargs and isinstance(kwargs["json"], ResourceModel):
            kwargs["json"] = self.model_instance_to_json(kwargs["json"])

        return await super().post(*args, **kwargs)

    async def _make_request(
        self,
        path: str,
        method: str,
        headers: dict | Headers | None,
        data: AnyStr | None,
        form: dict | None,
        files: dict[str, FileStorage] | None,
        query_string: dict | None,
        json: Any,
        scheme: str,
        root_path: str,
        http_version: str,
        scope_base: dict | None,
        auth: Authorization | tuple[str, str] | None = None,
        subdomain: str | None = None,
    ) -> Response:
        # TODO: Remove once we migrate to Quart
        # Copied from ``QuartClient._make_request`` so we can populate ``Content-Length`` header
        # Otherwise asgiref.wsgi.WsgiToAsgi won't pass length through, and Flask will ignore the request body

        headers, path, query_string_bytes = make_test_headers_path_and_query_string(
            self.app, path, headers, query_string, auth, subdomain
        )
        request_data, body_headers = make_test_body_with_headers(
            data=data, form=form, files=files, json=json, app=self.app
        )
        headers.update(**body_headers)
        if not headers.get("Content-Length"):
            headers.set("Content-Length", str(len(request_data)))

        if self.cookie_jar is not None:
            for cookie in self.cookie_jar:
                headers.add("cookie", f"{cookie.name}={cookie.value}")

        scope = make_test_scope(
            "http",
            path,
            method,
            headers,
            query_string_bytes,
            scheme,
            root_path,
            http_version,
            scope_base,
            _preserve_context=self.preserve_context,
        )
        async with self.http_connection_class(self.app, scope, _preserve_context=self.preserve_context) as connection:
            await connection.send(request_data)
            await connection.send_complete()
        response = await connection.as_response()
        if self.cookie_jar is not None:
            self.cookie_jar.extract_cookies(
                _TestCookieJarResponse(response.headers),  # type: ignore
                U2Request(f"{scheme}://{headers['host']}{path}"),
            )
        self.push_promises.extend(connection.push_promises)
        return response
