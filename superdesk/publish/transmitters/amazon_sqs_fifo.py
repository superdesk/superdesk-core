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
from botocore.exceptions import EndpointConnectionError, ConnectionClosedError, ClientError
from urllib3.exceptions import NewConnectionError

from superdesk.publish import publish_service, register_transmitter
from superdesk.errors import PublishAmazonSQSError

errors = [
    PublishAmazonSQSError.connectionError().get_error_description(),
    PublishAmazonSQSError.clientError().get_error_description(),
    PublishAmazonSQSError.sendMessageError().get_error_description(),
]


class AmazonSQSFIFOPublishService(publish_service.PublishService):
    """Amazon SQS FIFO Transmitter

    It creates a message on the Amazon SQS FIFO queue
    """

    NAME = "Amazon SQS FIFO"

    def _transmit(self, queue_item, subscriber):
        destination = queue_item.get("destination") or {}
        config = destination.get("config") or {}

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
                MessageBody=queue_item["formatted_item"],
                MessageGroupId=config.get("message_group_id"),
            )
        except (EndpointConnectionError, ConnectionClosedError, NewConnectionError) as error:
            raise PublishAmazonSQSError.connectionError(error, destination)
        except ClientError as error:
            raise PublishAmazonSQSError.clientError(error, destination)
        except Exception as error:
            raise PublishAmazonSQSError.sendMessageError(error, destination)

    def _transmit_media(self, media, destination):
        # Not supported
        pass


register_transmitter("amazon_sqs_fifo", AmazonSQSFIFOPublishService(), errors)
