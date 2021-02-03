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
from unittest.mock import MagicMock

from celery.exceptions import SoftTimeLimitExceeded

import superdesk
from superdesk.tests import TestCase


class SoftTimeLimitTestCase(TestCase):
    @mock.patch("superdesk.publish.registered_transmitters")
    def test_softtimeout_exception(self, *mocks):
        self.app.config["MAX_TRANSMIT_RETRY_ATTEMPT"] = 4
        self.app.config["CELERY_TASK_ALWAYS_EAGER"] = False
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

        items = [
            {
                "_id": ObjectId(),
                "state": "pending",
                "item_id": "item_1",
                "item_version": 4,
                "headline": "pending headline",
                "destination": {"delivery_type": "email"},
                "subscriber_id": subscriber["_id"],
                "formatted_item": "test",
            },
            {
                "_id": ObjectId(),
                "state": "pending",
                "item_id": "item_2",
                "item_version": 4,
                "headline": "pending headline 2",
                "destination": {"delivery_type": "email"},
                "subscriber_id": subscriber["_id"],
                "formatted_item": "test",
            },
        ]

        self.app.data.insert("publish_queue", items)

        fake_transmitter = MagicMock()
        fake_transmitter.transmit.side_effect = SoftTimeLimitExceeded()

        fake_transmitters_list = mocks[0]
        fake_transmitters_list.__getitem__.return_value = fake_transmitter

        with self.assertRaises(SoftTimeLimitExceeded):
            superdesk.publish.publish_content.transmit_subscriber_items(subscriber.get("_id"), False)
        failed_item = self.app.data.find_one("publish_queue", req=None, _id=items[0].get("_id"))
        self.assertEqual(failed_item["state"], "retrying")
        pending_item = self.app.data.find_one("publish_queue", req=None, _id=items[1].get("_id"))
        self.assertEqual(pending_item["state"], "pending")
        self.app.config["CELERY_TASK_ALWAYS_EAGER"] = True
