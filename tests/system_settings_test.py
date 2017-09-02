# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase

from eve.utils import config
from superdesk import get_backend
from superdesk.errors import SuperdeskApiError
from superdesk.system_settings.service import SystemSettingsService


class SystemSettingsTestCase(TestCase):

    def setUp(self):
        with self.app.app_context():
            self.service = SystemSettingsService('system_settings', backend=get_backend())

    def test_add_timedelta_property(self):
        with self.app.app_context():
            ids = self.service.create([{config.ID_FIELD: 'foo1', 'type': 'timedelta', 'value': '23d'}])
            doc = self.service.find_one(None, _id=ids[0])
            self.assertEqual(doc['value'], '23d')

            ids = self.service.create([{config.ID_FIELD: 'foo2', 'type': 'timedelta', 'value': '23h'}])
            doc = self.service.find_one(None, _id=ids[0])
            self.assertEqual(doc['value'], '23h')

            ids = self.service.create([{config.ID_FIELD: 'foo3', 'type': 'timedelta', 'value': '23m'}])
            doc = self.service.find_one(None, _id=ids[0])
            self.assertEqual(doc['value'], '23m')

            ids = self.service.create([{config.ID_FIELD: 'foo4', 'type': 'timedelta', 'value': '23s'}])
            doc = self.service.find_one(None, _id=ids[0])
            self.assertEqual(doc['value'], '23s')

            ids = self.service.create([{config.ID_FIELD: 'foo5', 'type': 'timedelta', 'value': '12d 12h 12m 12s'}])
            doc = self.service.find_one(None, _id=ids[0])
            self.assertEqual(doc['value'], '12d 12h 12m 12s')

            with self.assertRaises(SuperdeskApiError):
                self.service.post([{config.ID_FIELD: 'foo6', 'type': 'timedelta', 'value': '24h'}])

            with self.assertRaises(SuperdeskApiError):
                self.service.post([{config.ID_FIELD: 'foo7', 'type': 'timedelta', 'value': '60m'}])

            with self.assertRaises(SuperdeskApiError):
                self.service.post([{config.ID_FIELD: 'foo8', 'type': 'timedelta', 'value': '60s'}])

            with self.assertRaises(SuperdeskApiError):
                self.service.post([{config.ID_FIELD: 'foo9', 'type': 'timedelta', 'value': ''}])

            with self.assertRaises(SuperdeskApiError):
                self.service.post([{config.ID_FIELD: 'foo10', 'type': 'timedelta', 'value': '0d 0h 0m 0s'}])
