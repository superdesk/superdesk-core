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

    def setup(self):
        self.app_config = setup_config(self.app_config)
        self.app = SuperdeskAsyncApp(WSGI(config=self.app_config))
        self.app.start()

        for resource_config in self.app.mongo.get_all_resource_configs():
            client, db = self.app.mongo.get_client(resource_config.name)
            client.drop_database(db)

    def teardown(self):
        self.app.stop()

    async def asyncSetUp(self):
        self.app_config = setup_config(self.app_config)
        self.app = SuperdeskAsyncApp(WSGI(config=self.app_config))
        self.app.start()

        for resource_config in self.app.mongo.get_all_resource_configs():
            client, db = self.app.mongo.get_client_async(resource_config.name)
            await client.drop_database(db)

    async def asyncTearDown(self):
        self.app.stop()
