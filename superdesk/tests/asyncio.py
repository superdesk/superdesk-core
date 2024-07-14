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

from superdesk.core.app import SuperdeskAsyncApp

from . import setup_config


@dataclass
class WSGI:
    config: Dict[str, Any]


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    app: SuperdeskAsyncApp
    app_config: Dict[str, Any] = {}
    autorun: bool = True

    def setupApp(self):
        if getattr(self, "app", None):
            self.app.stop()

        self.app_config = setup_config(self.app_config)
        self.app = SuperdeskAsyncApp(WSGI(config=self.app_config))
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
