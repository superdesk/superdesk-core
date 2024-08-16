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

from apps.macros.macro_register import macros


class MacrosTestCase(TestCase):
    async def test_register(self):
        macros.register(name="test")
        self.assertIn("test", macros)

    async def test_load_modules(self):
        self.assertIn("usd_to_cad", macros)
        self.assertNotIn("foo name", macros)
