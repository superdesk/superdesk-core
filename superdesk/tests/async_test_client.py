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

from typing import Any, Callable, TypeVar

from asyncio import get_running_loop
from werkzeug import Response
from flask.testing import FlaskClient

from superdesk.core.resources.model import ResourceModel


T = TypeVar("T")


async def call(f: Callable[[], T]) -> T:
    loop = get_running_loop()
    return await loop.run_in_executor(executor=None, func=f)


class AsyncTestClient(FlaskClient):
    """A facade for the flask test client."""

    async_app = None

    def __init__(self, async_app, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.async_app = async_app

    def model_instance_to_json(self, model_instance: ResourceModel):
        return model_instance.model_dump(by_alias=True, exclude_unset=True, mode="json")

    async def _reset_db_connections(self):
        # TODO: Remove this when we migrate from Flask to Quart
        self.async_app.mongo.reset_all_async_connections()
        await self.async_app.elastic.reset_all_async_connections()

    async def get(self, *args, **kwargs) -> Response:
        parent = super()
        await self._reset_db_connections()

        response = await call(lambda: parent.get(*args, **kwargs))
        await self._reset_db_connections()
        return response

    async def post(self, *args, **kwargs) -> Response:
        parent = super()
        await self._reset_db_connections()

        if "json" in kwargs and isinstance(kwargs["json"], ResourceModel):
            kwargs["json"] = self.model_instance_to_json(kwargs["json"])

        response = await call(lambda: parent.post(*args, **kwargs))
        await self._reset_db_connections()
        return response

    async def patch(self, *args, **kwargs) -> Response:
        parent = super()
        await self._reset_db_connections()
        response = await call(lambda: parent.patch(*args, **kwargs))
        await self._reset_db_connections()
        return response

    async def delete(self, *args, **kwargs) -> Response:
        parent = super()
        await self._reset_db_connections()
        response = await call(lambda: parent.delete(*args, **kwargs))
        await self._reset_db_connections()
        return response

    async def put(self, *args, **kwargs) -> Response:
        parent = super()
        await self._reset_db_connections()
        response = await call(lambda: parent.put(*args, **kwargs))
        await self._reset_db_connections()
        return response
