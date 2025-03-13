# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase

from superdesk import get_resource_service
from apps.macros.macro_register import macros


class MacrosTestCase(TestCase):
    async def test_register(self):
        def run_macro():
            pass

        macros.register(name="test", callback=run_macro)
        self.assertIn("test", macros)

    async def test_run_async_macros(self):
        def sync_macro(item: dict):
            return {
                **item,
                "status": "OK",
                "type": "sync"
            }

        async def async_macro(item: dict):
            return {
                **item,
                "status": "OK",
                "type": "async"
            }

        macros.register(name="sync_macro", callback=sync_macro)
        macros.register(name="async_macro", callback=async_macro)

        service = get_resource_service("macros")
        response = await service.execute_macro({"name": "foo"}, "sync_macro")
        self.assertEqual(response, {"name": "foo", "status": "OK", "type": "sync"})

        response = await service.execute_macro({"name": "foo"}, "async_macro")
        self.assertEqual(response, {"name": "foo", "status": "OK", "type": "async"})

    async def test_load_modules(self):
        self.assertIn("usd_to_cad", macros)
        self.assertNotIn("foo name", macros)
