# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2021 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import asyncio
import logging

from aiohttp import ClientConnectionError
import aioboto3
from botocore.exceptions import EndpointConnectionError, ConnectionClosedError, ClientError, NoCredentialsError

from superdesk.publish import publish_service, register_transmitter
from superdesk.errors import PublishAmazonSQSError

logger = logging.getLogger(__name__)
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
            if destination.get("name") == name and destination.get("delivery_type") == delivery_type:
                return destination

        return {}

    async def _send_to_sqs(self, config, message_body, destination):
        try:
            session = aioboto3.Session()
            async with session.client(
                "sqs",
                aws_access_key_id=config.get("access_key_id"),
                aws_secret_access_key=config.get("secret_access_key"),
                region_name=config.get("region"),
                endpoint_url=config.get("endpoint_url"),
            ) as sqs:
                response = await sqs.get_queue_url(QueueName=config.get("queue_name"))
                queue_url = response["QueueUrl"]

                await sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=message_body,
                    MessageGroupId=config.get("message_group_id"),
                )
        except NoCredentialsError:
            raise
        except (EndpointConnectionError, ConnectionClosedError, ClientConnectionError) as error:
            raise await PublishAmazonSQSError.connectionError(error, destination).send_notifications()
        except ClientError as error:
            raise await PublishAmazonSQSError.clientError(error, destination).send_notifications()
        except asyncio.TimeoutError as error:
            raise await PublishAmazonSQSError.connectionError(error, destination).send_notifications()
        except asyncio.CancelledError:
            logger.exception("AmazonSQSFIFOPublishService Asyncio Task Cancelled")
            raise
        except Exception as error:
            raise await PublishAmazonSQSError.sendMessageError(error, destination).send_notifications()

    async def _transmit(self, queue_item, subscriber):
        destination = queue_item.get("destination") or {}
        config = destination.get("config") or {}
        message_body = queue_item["formatted_item"]

        try:
            return await self._send_to_sqs(config, message_body, destination)
        except NoCredentialsError:
            # Retry using the matching destination's config from the subscriber
            subscriber_destination = self._find_matching_destination(subscriber, destination) or {}
            fallback_config = subscriber_destination.get("config") or {}
            try:
                return await self._send_to_sqs(fallback_config, message_body, destination)
            except NoCredentialsError as error:
                raise PublishAmazonSQSError.credentialsError(error, destination)

    async def _transmit_media(self, media, destination):
        # Not supported
        pass


register_transmitter("amazon_sqs_fifo", AmazonSQSFIFOPublishService(), errors)
