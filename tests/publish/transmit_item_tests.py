# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId
from unittest import mock
from unittest.mock import MagicMock, ANY
from datetime import timedelta

from superdesk.tests import TestCase
from superdesk.utc import utcnow
from superdesk.errors import PublishHTTPPushServerError, PublishHTTPPushClientError
from superdesk.publish.publish_content import transmit_item


class TransmitItemTestCase(TestCase):
    """Tests for the transmit_item() function."""

    def setUp(self):
        self.func_under_test = transmit_item

    @mock.patch("superdesk.publish.publish_content.get_resource_service")
    def test_marks_items_as_retrying_in_case_of_failure(self, *mocks):
        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception("Error patching item")

        item_1 = {
            "_id": "item_1",
            "destination": {},
            "subscriber_id": "1",
            "item_id": "test",
            "headline": "test headline",
            "item_version": 4,
            "state": "pending",
        }

        orig_item = item_1.copy()  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item

        with self.assertRaises(Exception):
            self.func_under_test(item_1["_id"])
        fake_get_service().system_update.assert_called_with(
            "item_1",
            {"_updated": ANY, "retry_attempt": 1, "state": "retrying", "next_retry_attempt_at": ANY},
            orig_item,
        )

    @mock.patch("superdesk.publish.publish_content.get_resource_service")
    def test_marks_items_as_retrying_second_time_incase_of_failure(self, *mocks):

        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception("Error patching item")

        item_1 = {
            "_id": "item_1",
            "destination": {},
            "subscriber_id": "1",
            "item_id": "test",
            "headline": "test headline",
            "item_version": 4,
            "state": "retrying",
            "retry_attempt": 1,
            "next_retry_attempt_at": utcnow() - timedelta(minutes=10),
        }

        orig_item = item_1.copy()  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item
        with self.assertRaises(Exception):
            self.func_under_test(item_1["_id"])

        fake_get_service().system_update.assert_called_with(
            "item_1",
            {"_updated": ANY, "retry_attempt": 2, "state": "retrying", "next_retry_attempt_at": ANY},
            orig_item,
        )

    @mock.patch("superdesk.publish.publish_content.get_resource_service")
    def test_marks_items_failed_to_transmit_after_all_retry_attempts(self, *mocks):

        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception("Error patching item")
        self.app.config["MAX_TRANSMIT_RETRY_ATTEMPT"] = 4

        item_1 = {
            "_id": "item_1",
            "destination": {},
            "subscriber_id": "1",
            "item_id": "test",
            "headline": "test headline",
            "item_version": 4,
            "state": "retrying",
            "retry_attempt": 4,
            "next_retry_attempt_at": utcnow() - timedelta(minutes=10),
        }

        orig_item = item_1.copy()  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item
        with self.assertRaises(Exception):
            self.func_under_test(item_1["_id"])
        fake_get_service().system_update.assert_called_with("item_1", {"_updated": ANY, "state": "failed"}, orig_item)

    @mock.patch("superdesk.publish.publish_content.logger")
    @mock.patch("superdesk.publish.publish_content.get_resource_service")
    def test_logs_error_even_when_marking_failed_items_fails(self, *mocks):
        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception("Error patching item")
        fake_get_service().system_update.side_effect = Exception("Update error")

        item_1 = {
            "_id": "item_1",
            "subscriber_id": "1",
            "destination": {},
            "item_id": "test",
            "headline": "test headline",
            "item_version": 4,
            "state": "pending",
        }

        fake_get_service().find_one.return_value = item_1
        with self.assertRaises(Exception):
            self.func_under_test(item_1["_id"])
        fake_logger = mocks[1]
        expected_msg = "Failed to set the state for failed publish queue item item_1."
        fake_logger.error.assert_any_call(expected_msg)

    def test_transmit_failure(self):
        subscriber = {
            "_id": ObjectId("56c11bd78b84bb00b0a1905e"),
            "sequence_num_settings": {"max": 9999, "min": 1},
            "_etag": "f16b7eaa566f68b8d2561c811ec694bdf819784d",
            "is_active": True,
            "destinations": [{"delivery_type": "email"}],
            "email": "test@test.com",
            "subscriber_type": "digital",
            "name": "Test",
        }

        self.app.data.insert("subscribers", [subscriber])

        item_1 = {
            "_id": ObjectId(),
            "state": "pending",
            "item_id": "item_1",
            "item_version": 4,
            "headline": "pending headline",
            "destination": {"delivery_type": "email"},
            "subscriber_id": subscriber["_id"],
            "formatted_item": "test",
        }

        self.app.data.insert("publish_queue", [item_1])
        self.assertIsNone(self.func_under_test(item_1["_id"]))
        failed_item = self.app.data.find_one("publish_queue", req=None, _id=item_1["_id"])
        self.assertEqual(failed_item["state"], "retrying")
        self.assertEqual(failed_item["retry_attempt"], 1)
        self.assertEqual(failed_item["next_retry_attempt_at"], ANY)

    @mock.patch("superdesk.publish.publish_content.get_resource_service")
    @mock.patch("superdesk.publish.registered_transmitters")
    def test_no_retry_on_http_push_client_error(self, *mocks):
        self.app.config["MAX_TRANSMIT_RETRY_ATTEMPT"] = 4

        item_1 = {
            "_id": "item_1",
            "destination": {},
            "subscriber_id": "1",
            "item_id": "test",
            "headline": "test headline",
            "item_version": 4,
            "state": "pending",
        }

        orig_item = item_1.copy()  # item's original state in DB

        fake_get_service = mocks[1]
        fake_get_service().find_one.return_value = orig_item

        fake_transmitter = MagicMock()
        fake_transmitter.transmit.side_effect = PublishHTTPPushClientError.httpPushError(Exception("client 4xx"))

        fake_transmitters_list = mocks[0]
        fake_transmitters_list.__getitem__.return_value = fake_transmitter

        self.assertIsNone(self.func_under_test(item_1["_id"]))

        fake_get_service().system_update.assert_called_with("item_1", {"_updated": ANY, "state": "failed"}, orig_item)

    @mock.patch("superdesk.publish.publish_content.get_resource_service")
    @mock.patch("superdesk.publish.registered_transmitters")
    def test_retry_on_http_push_server_error(self, *mocks):
        self.app.config["MAX_TRANSMIT_RETRY_ATTEMPT"] = 4

        item_1 = {
            "_id": "item_1",
            "destination": {},
            "subscriber_id": "1",
            "item_id": "test",
            "headline": "test headline",
            "item_version": 4,
            "state": "pending",
        }

        orig_item = item_1.copy()  # item's original state in DB

        fake_get_service = mocks[1]
        fake_get_service().find_one.return_value = orig_item

        fake_transmitter = MagicMock()
        fake_transmitter.transmit.side_effect = PublishHTTPPushServerError.httpPushError(Exception("server 5xx"))

        fake_transmitters_list = mocks[0]
        fake_transmitters_list.__getitem__.return_value = fake_transmitter

        self.assertIsNone(self.func_under_test(item_1["_id"]))

        fake_get_service().system_update.assert_called_with(
            "item_1",
            {"_updated": ANY, "retry_attempt": 1, "state": "retrying", "next_retry_attempt_at": ANY},
            orig_item,
        )
