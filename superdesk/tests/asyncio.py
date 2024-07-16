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
import unittest
from dataclasses import dataclass

from werkzeug import Response

from superdesk.factory.app import SuperdeskApp
from superdesk.core.app import SuperdeskAsyncApp

from . import setup_config, setup
from .async_test_client import AsyncTestClient


@dataclass
class MockWSGI:
    config: Dict[str, Any]

    def add_url_rule(self, *args, **kwargs):
        pass

    def register_endpoint(self, endpoint):
        pass

    def register_endpoint_group(self, group):
        pass


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    app: SuperdeskAsyncApp
    app_config: Dict[str, Any] = {}
    autorun: bool = True

    def setupApp(self):
        if getattr(self, "app", None):
            self.app.stop()

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


class AsyncFlaskTestCase(AsyncTestCase):
    async_app: SuperdeskAsyncApp
    app: SuperdeskApp
    test_client: AsyncTestClient

    async def asyncSetUp(self):
        if getattr(self, "async_app", None):
            self.async_app.stop()
            await self.async_app.elastic.stop()

        setup(self, config=self.app_config, reset=True)
        self.async_app = self.app.async_app
        self.test_client = AsyncTestClient(self.async_app, self.app, Response, True)
        self.ctx = self.app.app_context()
        self.ctx.push()

        def clean_ctx():
            if self.ctx:
                try:
                    self.ctx.pop()
                except Exception:
                    pass

        self.addCleanup(clean_ctx)
        self.async_app.elastic.init_all_indexes()

    async def asyncTearDown(self):
        if not getattr(self, "async_app", None):
            return

        self.async_app.elastic.drop_indexes()
        self.async_app.stop()
        await self.async_app.elastic.stop()
