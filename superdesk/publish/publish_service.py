# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from typing import Any, Dict, Optional
from inspect import isawaitable
from bson import ObjectId

from superdesk.core import get_current_app
from superdesk.utc import utcnow
from superdesk.errors import SubscriberError, SuperdeskPublishError, PublishQueueError
from superdesk.types import PublishQueueResource, SubscribersResource

logger = logging.getLogger(__name__)
extensions = {"NITF": "ntf", "XML": "xml", "NINJS": "json"}


class PublishServiceBase:
    """Base publish service class."""

    NAME: Optional[str] = None
    CONFIG: Dict[str, Any] = {}
    DEFAULT_EXT = "txt"

    def _transmit(self, queue_item, subscriber):
        """Performs the publishing of the queued item. Implement in subclass

        @param queue_item: the queued item document
        @type queue_item: dict
        @param subscriber: the subscriber document
        @type subscriber: dict
        """
        raise NotImplementedError()

    def _transmit_media(self, media, destination):
        """Transmit media file. Implement in subclass"""
        raise NotImplementedError()

    async def transmit(self, queue_item):
        subscriber = await SubscribersResource.get_service().find_by_id(queue_item["subscriber_id"])

        if not subscriber.is_active:
            raise await SubscriberError.subscriber_inactive_error(
                Exception("Subscriber inactive"), subscriber
            ).send_notifications()
        else:
            try:
                # "formatted_item" is the item as str
                # "encoded_item" is the bytes version
                # if "encoded_item_id" exists we use it, else
                # we fill encoded_item using "formatted_item" and "item_encoding"
                if "encoded_item_id" in queue_item:
                    encoded_item_id = queue_item["encoded_item_id"]
                    async_file = await get_current_app().storage.get_async(encoded_item_id)
                    queue_item["encoded_item"] = await async_file.to_bytes()
                else:
                    encoding = queue_item.get("item_encoding", "utf-8")
                    queue_item["encoded_item"] = queue_item["formatted_item"].encode(encoding, errors="replace")

                transmit_response = self._transmit(queue_item, subscriber) or []
                if isawaitable(transmit_response):
                    await transmit_response
                await self.update_item_status(queue_item["_id"], "success")
            except SuperdeskPublishError as error:
                await self.update_item_status(queue_item["_id"], "error", error)
                await self.close_transmitter(subscriber, error)
                raise error

    async def transmit_media(self, media, subscriber=None, destination=None):
        if subscriber and destination and subscriber.get("is_active"):
            transmit_response = self._transmit_media(media, destination)
            if isawaitable(transmit_response):
                transmit_response = await transmit_response

            return transmit_response

    async def close_transmitter(self, subscriber: SubscribersResource, error: SuperdeskPublishError) -> None:
        """
        Checks if the transmitter has the error code set in the list of critical errors then closes the transmitter.

        :param subscriber: The subscriber that should be closed
        :param error: The error thrown during transmission
        """

        if not subscriber.critical_errors or not subscriber.critical_errors.get(str(error.code)):
            return

        updates = {
            "is_active": False,
            "last_closed": {
                "closed_at": utcnow(),
                "message": "Subscriber made inactive due to critical error: {}".format(error),
            },
        }

        await SubscribersResource.get_service().system_update(subscriber.id, updates)

    async def update_item_status(
        self,
        queue_item_id: ObjectId,
        status: str,
        error: SuperdeskPublishError | None = None,
    ) -> None:
        try:
            item_update = {"state": status}
            if status == "in-progress":
                item_update["transmit_started_at"] = utcnow()
            elif status == "success":
                item_update["completed_at"] = utcnow()
            elif status == "error" and error:
                item_update["error_message"] = "{}:{}".format(error, str(error.system_exception))

            await PublishQueueResource.get_service().update(queue_item_id, item_update)
        except Exception as ex:
            raise await PublishQueueError.item_update_error(ex).send_notifications()

    @classmethod
    def get_file_extension(cls, queue_item):
        try:
            format_ = queue_item["destination"]["format"].upper()
        except KeyError:
            pass
        else:
            # "in" is used in addition of equality, so subclass can inherit extensions
            # e.g.: "NITF" will work for "NTB NITF"
            try:
                return extensions[format_]
            except KeyError:
                for f, ext in extensions.items():
                    if f in format_:
                        return ext
        # nothing found, we return default extension
        return cls.DEFAULT_EXT

    @classmethod
    def get_filename(cls, queue_item):
        config = queue_item.get("destination", {}).get("config", {})
        # use the file extension from config if it is set otherwise use extension for the format
        extension = config.get("file_extension") or cls.get_file_extension(queue_item)

        return "{}-{}-{}.{}".format(
            queue_item["item_id"],
            str(queue_item.get("item_version", "")),
            str(queue_item.get("published_seq_num", "")),
            extension,
        ).replace(":", "-")

    @staticmethod
    def register_file_extension(format_, ext):
        """Register new file extension

        :param format_: item format
        :param ext: extension to use
        """
        if format_ in extensions:
            logger.warning("overriding existing extension for {}".format(format_))
        extensions[format_.upper()] = ext


PublishService = PublishServiceBase


def get_publish_service():
    return PublishService


def set_publish_service(publish_service_class):
    global PublishService
    PublishService = publish_service_class
