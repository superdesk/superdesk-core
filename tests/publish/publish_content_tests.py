# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import unittest

from unittest import mock
from unittest.mock import MagicMock

from superdesk.publish.publish_content import STATE_PENDING


class TransmitItemsTestCase(unittest.TestCase):
    """Tests for the transmit_items() function."""

    def setUp(self):
        try:
            from superdesk.publish.publish_content import transmit_items
        except ImportError:
            self.fail("Could not import function under test (transmit_items).")
        else:
            self.func_under_test = transmit_items

    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    @mock.patch(
        'superdesk.publish.publish_content.is_on_time',
        return_value=True)
    def test_marks_items_failed_to_transmit_as_pending(self, *mocks):

        fake_get_service = mocks[1]
        fake_get_service().patch.side_effect = Exception('Error patching item')

        orig_item = MagicMock(name='orig_item')  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item

        item_1 = {
            '_id': 'item_1',
            'destination': {}
        }

        queue_items = [item_1]
        self.func_under_test(queue_items)

        fake_get_service().system_update.assert_called_with(
            'item_1', {'state': STATE_PENDING}, orig_item)

    @mock.patch('superdesk.publish.publish_content.logger')
    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    @mock.patch(
        'superdesk.publish.publish_content.is_on_time',
        return_value=True)
    def test_logs_error_even_when_marking_failed_items_fails(self, *mocks):

        fake_get_service = mocks[1]
        fake_get_service().patch.side_effect = Exception('Error patching item')
        fake_get_service().find_one.return_value = MagicMock(name='orig_item')
        fake_get_service().system_update.side_effect = Exception('Update error')

        item_1 = {
            '_id': 'item_1',
            'destination': {}
        }
        queue_items = [item_1]

        self.func_under_test(queue_items)

        fake_logger = mocks[2]
        expected_msg = (
            'Failed to set the publish queue item back to '
            '"pending" state: item_1')
        fake_logger.error.assert_any_call(expected_msg)
