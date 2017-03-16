# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import logging

from superdesk.tests import TestCase
from .remove_expired_items import RemoveExpiredItems
from superdesk import get_resource_service
from datetime import timedelta
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)

utc = utcnow()
expired = utc - timedelta(days=10)
not_expired = utc - timedelta(days=1)
items = [
    {'_id': '1', '_updated': not_expired, 'type': 'text'},  # Single item, not expired

    {'_id': '2', '_updated': expired, 'type': 'text'},  # Single item, expired

    # Evolved from: parent expired, child not expired
    {'_id': '3', '_updated': expired, 'type': 'text'},
    {'_id': '4', '_updated': not_expired, 'type': 'text', 'evolvedfrom': '3', 'ancestors': ['3']},

    # Evolved from: parent expired, child expired
    {'_id': '5', '_updated': expired, 'type': 'text'},
    {'_id': '6', '_updated': expired, 'type': 'text', 'evolvedfrom': '5', 'ancestors': ['5']},

    # Multi-branch evolved from,
    {'_id': '7', '_updated': expired, 'type': 'text'},
    {'_id': '8', '_updated': expired, 'type': 'text', 'evolvedfrom': '7', 'ancestors': ['7']},
    {'_id': '9', '_updated': not_expired, 'type': 'text', 'evolvedfrom': '8', 'ancestors': ['7', '8']},

    # Multi-branch evolved from
    {'_id': '10', '_updated': expired, 'type': 'text'},
    {'_id': '11', '_updated': expired, 'type': 'text', 'evolvedfrom': '10', 'ancestors': ['10']},
    {'_id': '12', '_updated': expired, 'type': 'text', 'evolvedfrom': '11', 'ancestors': ['10', '11']},
]

can_expire = [
    '2',  # Single item, expired
    '5', '6',  # Evolved from, parent expired, child expired
    '10', '11', '12'  # Multi-branch evolved from
]


class RemoveExpiredItemsTest(TestCase):
    def setUp(self):
        self.app.data.insert('items', items)
        self.command = RemoveExpiredItems()
        self.command.expiry_days = 8
        self.now = utcnow()

    def _get_items(self):
        return list(get_resource_service('items').get_from_mongo(req=None, lookup=None))

    def test_remove_expired_items(self):
        self.command._remove_expired_items(self.now, self.command.expiry_days)
        items = self._get_items()

        self.assertEqual(len(items), 6)
        for item in items:
            self.assertNotIn(item['_id'], can_expire)

    def test_get_expired_chain(self):
        items_service = get_resource_service('items')
        for item in self._get_items():
            if self.command._get_expired_chain(items_service, item, self.now):
                self.assertTrue(item['_id'] in can_expire)
            else:
                self.assertFalse(item['_id'] in can_expire)

    def test_run(self):
        self.command.run(self.command.expiry_days)
        items = self._get_items()

        self.assertEqual(len(items), 6)
        for item in items:
            self.assertNotIn(item['_id'], can_expire)

    def test_has_expired(self):
        has_expired = self.command._has_expired(items[1], self.now)
        self.assertTrue(has_expired)

        has_expired = self.command._has_expired(items[0], self.now)
        self.assertFalse(has_expired)

    def test_get_children(self):
        service = get_resource_service('items')
        children = self.command._get_children(service, items[0])
        self.assertEqual(children, [])

        children = [child['_id'] for child in self.command._get_children(service, items[2])]
        self.assertEqual(children, ['4'])

        children = [child['_id'] for child in self.command._get_children(service, items[9])]
        self.assertEqual(children, ['11', '12'])
