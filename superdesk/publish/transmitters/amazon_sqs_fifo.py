# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2021 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import boto3
from botocore.exceptions import EndpointConnectionError, ConnectionClosedError, ClientError, NoCredentialsError
from urllib3.exceptions import NewConnectionError

from superdesk.publish import publish_service, register_transmitter
from superdesk.errors import PublishAmazonSQSError

errors = [
    PublishAmazonSQSError.connectionError().get_error_description(),
    PublishAmazonSQSError.clientError().get_error_description(),
    PublishAmazonSQSError.sendMessageError().get_error_description(),
    PublishAmazonSQSError.credentialsError().get_error_description(),
]


class AmazonSQSFIFOPublishService(publish_service.PublishService):
    """Amazon SQS FIFO Transmitter

    It creates a message on the Amazon SQS FIFO queue
    """

    NAME = "Amazon SQS FIFO"

    def _find_matching_destination(self, subscriber, target_destination):
        if not subscriber:
            return {}

        destinations = subscriber.get("destinations") or []
        delivery_type = (target_destination or {}).get("delivery_type")
        name = (target_destination or {}).get("name")

        if not delivery_type or not name or not destinations:
            return {}

        for destination in destinations:
            if delivery_type and destination.get("name") == name and destination.get("delivery_type"):
                return destination

        return {}

    def _send_to_sqs(self, config, message_body, destination):
        try:
            sqs = boto3.resource(
                "sqs",
                aws_access_key_id=config.get("access_key_id"),
                aws_secret_access_key=config.get("secret_access_key"),
                region_name=config.get("region"),
                endpoint_url=config.get("endpoint_url"),
            )
            queue = sqs.get_queue_by_name(QueueName=config.get("queue_name"))
            queue.send_message(
                MessageBody=message_body,
                MessageGroupId=config.get("message_group_id"),
            )
        except NoCredentialsError:
            raise
        except (EndpointConnectionError, ConnectionClosedError, NewConnectionError) as error:
            raise PublishAmazonSQSError.connectionError(error, destination)
        except ClientError as error:
            raise PublishAmazonSQSError.clientError(error, destination)
        except Exception as error:
            raise PublishAmazonSQSError.sendMessageError(error, destination)

    def _transmit(self, queue_item, subscriber):
        destination = queue_item.get("destination") or {}
        config = destination.get("config") or {}
        message_body = queue_item["formatted_item"]

        try:
            return self._send_to_sqs(config, message_body, destination)
        except NoCredentialsError:
            # Retry using the matching destination's config from the subscriber
            subscriber_destination = self._find_matching_destination(subscriber, destination) or {}
            fallback_config = subscriber_destination.get("config") or {}
            try:
                return self._send_to_sqs(fallback_config, message_body, destination)
            except NoCredentialsError as error:
                raise PublishAmazonSQSError.credentialsError(error, destination)

    def _transmit_media(self, media, destination):
        # Not supported
        pass


register_transmitter("amazon_sqs_fifo", AmazonSQSFIFOPublishService(), errors)
