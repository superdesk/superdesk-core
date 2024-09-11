# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2021 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import boto3

from moto import mock_aws
from unittest import TestCase, mock

from superdesk.publish.transmitters.amazon_sqs_fifo import AmazonSQSFIFOPublishService
from superdesk.errors import PublishAmazonSQSError


class AmazonSQSFIFOPublishServiceTestCase(TestCase):
    def setUp(self):
        self.config = {
            "region": "ap-southeast-2",
            "access_key_id": "abcd123",
            "secret_access_key": "efgh456",
            "queue_name": "mock_queue.fifo",
            "message_group_id": "tests",
        }
        self.formatted_item1 = {
            "_id": "item1",
            "headline": "headline",
            "versioncreated": "2015-03-09T16:32:23",
            "version": 1,
        }
        self.item = {
            "item_id": "item1",
            "format": "ninjs",
            "item_version": 1,
            "published_seq_num": 1,
            "formatted_item": json.dumps(self.formatted_item1),
            "destination": {
                "name": "test",
                "delivery_type": "amazon_sqs_fifo",
                "format": "ninjs",
                "config": self.config,
            },
        }

        self.mock_aws = mock_aws()
        self.mock_aws.start()

        self.sqs = boto3.resource(
            "sqs",
            aws_access_key_id=self.config["access_key_id"],
            aws_secret_access_key=self.config["secret_access_key"],
            region_name=self.config["region"],
        )
        self.service = AmazonSQSFIFOPublishService()

    def tearDown(self) -> None:
        self.mock_aws.stop()
        return super().tearDown()

    def _create_queue(self):
        self.sqs.create_queue(
            QueueName=self.config["queue_name"],
            Attributes={
                "ContentBasedDeduplication": "true",
                "FifoQueue": "true",
            },
        )

    def _get_queue_messages(self):
        queue = self.sqs.get_queue_by_name(QueueName=self.config["queue_name"])
        return queue.receive_messages()

    def test_publish_an_item(self):
        self._create_queue()

        self.service._transmit(self.item, {})
        messages = self._get_queue_messages()
        item = json.loads(messages[0].body)
        self.assertDictEqual(item, self.formatted_item1)

    @mock.patch("superdesk.errors.notifications_enabled", return_value=False)
    def test_connection_error(self, _notifications_enabled):
        self.config["endpoint_url"] = "http://abcd"

        with self.assertRaises(PublishAmazonSQSError) as context:
            self.service._transmit(self.item, {})

        ex = context.exception
        self.assertEqual(str(ex), "PublishAmazonSQSError Error 15000 - Amazon SQS publish connection error")
        self.assertEqual(ex.code, 15000)

    @mock.patch("superdesk.errors.notifications_enabled", return_value=False)
    def test_client_error(self, _notifications_enabled):
        self._create_queue()
        self.config["queue_name"] = "missing_queue.fifo"

        with self.assertRaises(PublishAmazonSQSError) as context:
            self.service._transmit(self.item, {})

        ex = context.exception
        self.assertEqual(str(ex), "PublishAmazonSQSError Error 15001 - Amazon SQS publish client error")
        self.assertEqual(ex.code, 15001)

    @mock.patch("superdesk.errors.notifications_enabled", return_value=False)
    def test_send_message_error(self, _notifications_enabled):
        self._create_queue()
        self.item["formatted_item"] = None

        with self.assertRaises(PublishAmazonSQSError) as context:
            self.service._transmit(self.item, {})

        ex = context.exception
        self.assertEqual(str(ex), "PublishAmazonSQSError Error 15002 - Amazon SQS publish sendMessage error")
        self.assertEqual(ex.code, 15002)
