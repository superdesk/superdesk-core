# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any
import os
import unittest
from dataclasses import dataclass
from quart import Response
from quart.testing import QuartClient

from superdesk.factory.app import SuperdeskApp
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core import app as core_app
from superdesk.core.resources import ResourceModel

from . import setup_config, setup


@dataclass
class MockWSGI:
    config: Dict[str, Any]

    def add_url_rule(self, *args, **kwargs):
        pass

    def register_endpoint(self, endpoint):
        pass


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    app: SuperdeskAsyncApp
    app_config: Dict[str, Any] = {}
    autorun: bool = True

    def setupApp(self):
        if getattr(self, "app", None):
            self.app.stop()

        core_app._global_app = None

        self.app_config = setup_config(self.app_config)
        self.app = SuperdeskAsyncApp(MockWSGI(config=self.app_config))
        self.app.start()

    async def asyncSetUp(self):
        if not self.autorun:
            return

        self.setupApp()
        for resource_name, resource_config in self.app.mongo.get_all_resource_configs().items():
            client, db = self.app.mongo.get_client_async(resource_name)
            await client.drop_database(db)

    async def asyncTearDown(self):
        if not getattr(self, "app", None):
            return

        self.app.elastic.drop_indexes()
        self.app.stop()
        await self.app.elastic.stop()

    def get_fixture_path(self, filename):
        rootpath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(rootpath, "features", "steps", "fixtures", filename)


class TestClient(QuartClient):
    def model_instance_to_json(self, model_instance: ResourceModel):
        return model_instance.model_dump(by_alias=True, exclude_unset=True, mode="json")

    async def post(self, *args, **kwargs) -> Response:
        if "json" in kwargs and isinstance(kwargs["json"], ResourceModel):
            kwargs["json"] = self.model_instance_to_json(kwargs["json"])

        return await super().post(*args, **kwargs)


class AsyncFlaskTestCase(AsyncTestCase):
    async_app: SuperdeskAsyncApp
    app: SuperdeskApp

    async def asyncSetUp(self):
        if getattr(self, "async_app", None):
            self.async_app.stop()
            await self.async_app.elastic.stop()

        await setup(self, config=self.app_config, reset=True)
        self.async_app = self.app.async_app
        self.app.test_client_class = TestClient
        self.test_client = self.app.test_client()
        self.ctx = self.app.app_context()
        await self.ctx.push()

        async def clean_ctx():
            if self.ctx:
                try:
                    await self.ctx.pop()
                except Exception:
                    pass

        self.addAsyncCleanup(clean_ctx)
        self.async_app.elastic.init_all_indexes()

    async def asyncTearDown(self):
        if not getattr(self, "async_app", None):
            return

        self.async_app.elastic.drop_indexes()
        self.async_app.stop()
        await self.async_app.elastic.stop()
