# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime

from bson import ObjectId
from eve.utils import date_to_str

from superdesk.tests import TestCase
from superdesk.celery_app import try_cast, loads


class CeleryTestCase(TestCase):
    _id = ObjectId("528de7b03b80a13eefc5e610")

    def test_cast_objectid(self):
        self.assertEqual(try_cast(str(self._id)), self._id)

    async def test_cast_datetime(self):
        date = datetime(2012, 12, 12, 12, 12, 12, 0)
        s = date_to_str(date)
        self.assertEqual(try_cast(s).day, date.day)

    async def test_loads_args(self):
        s = b'{"args": [{"_id": "528de7b03b80a13eefc5e610", "_updated": "2014-09-10T14:31:09+0000"}]}'
        o = loads(s)
        self.assertEqual(o["args"][0]["_id"], self._id)
        self.assertIsInstance(o["args"][0]["_updated"], datetime)

    def test_loads_kwargs(self):
        s = b"""{"kwargs": "{}", "pid": 24998, "eta": null}"""
        o = loads(s)
        self.assertEqual({}, o["kwargs"])
        self.assertIsNone(o["eta"])

    def test_loads_lists(self):
        s = b"""[{}, {"foo": null}]"""
        o = loads(s)
        self.assertEqual([{}, {"foo": None}], o)

    def test_loads_zero(self):
        s = b"""[0]"""
        o = loads(s)
        self.assertEqual([0], o)

    def test_loads_boolean(self):
        s = b"""[{"foo": false, "bar": true}]"""
        o = loads(s)
        self.assertEqual([{"foo": False, "bar": True}], o)
