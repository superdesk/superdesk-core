# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from superdesk.utils import SuperdeskBaseEnum


class EnumToTest(SuperdeskBaseEnum):
    red = 1
    blue = 2
    green = 3


class EnumTestCase(TestCase):
    def test_enum_from_value(self):
        self.assertEqual(EnumToTest.from_value(1), EnumToTest.red)
        self.assertIsNone(EnumToTest.from_value(4))

    def test_enum_values(self):
        values = EnumToTest.values()
        self.assertIn(1, values)
        self.assertIn(2, values)
        self.assertIn(3, values)
        self.assertNotIn(4, values)
