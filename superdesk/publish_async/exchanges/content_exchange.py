import logging

from bson import ObjectId
from celery.exceptions import SoftTimeLimitExceeded

# TODO-ASYNC: Replace resolve_document_version with something from async core lib
from eve.versioning import resolve_document_version

from superdesk.core import get_current_app
from superdesk.types import PublishRequest, PublishRequestResponse, PublishState
from superdesk import get_resource_service
import superdesk.signals as signals
from superdesk.resource_fields import ID_FIELD, VERSION, ITEM_STATE
from superdesk.metadata.item import CONTENT_STATE
from superdesk.errors import ConnectionTimeout
from superdesk.utc import utcnow

from apps.archive.common import ARCHIVE, insert_into_versions
from apps.content import push_content_notification
from apps.publish.content.common import get_utc_publish_schedule, ITEM_PUBLISH
from apps.publish.published_item import QUEUE_STATE, PUBLISHED, ERROR_MESSAGE
from apps.legal_archive.commands import import_into_legal_archive

import content_api

from .base_exchange import BasicPublishExchange

logger = logging.getLogger(__name__)


class ContentPublishExchange(BasicPublishExchange):
    """
    Class ContentPublishExchange is responsible for handling the publication
    of content items in a distributed system. It facilitates the management
    and updating of published content states, handles scheduling, and provides
    capabilities to route publication requests asynchronously.

    This class extends BasicPublishExchange and integrates with various
    services and tasks for state management, error handling, and content
    scheduling. It ensures that the publication process is synchronized with
    multiple systems such as archives, notifications, and legal archives.
    """

    name = "content"

    async def send(self, request: PublishRequest) -> PublishRequestResponse:
        """
        Asynchronously sends a ``PublishRequest`` to update the state of a published item. The function
        handles different cases for the items based on their current state or scheduled time. If the item
        is not found in the existing published collection, it logs a warning and returns a response
        indicating that it was not routed. Attempts to update or set the appropriate state (e.g., pending,
        queued, queued_not_transmitted) for the published item depending on circumstances and responds
        with the appropriate status.

        :param request: The publication request containing the details for publishing.
        :return: The response object that contains the result of the publication processing and routing.
        :raises superdesk.errors.ConnectionTimeout: If there is a recoverable connection timeout error
                during the operation. Sets the queue state to pending and adds relevant error messages.
        :raises celery.exceptionsSoftTimeLimitExceeded: If the celery time limit is exceeded while
                processing the request. Sets the queue state to pending and adds relevant error messages.
        :raises Exception: For all other unexpected errors during processing. Sets the queue state
                to error and logs appropriate messages to help debugging.
        """

        # Update the ``published`` collection, to update it's state
        published_service = get_resource_service(PUBLISHED)

        published_item = published_service.find_one(
            req=None, item_id=request.item_id, _current_version=request.item[VERSION]
        )
        if not published_item:
            # If we failed to get the item by ``_current_version``, then try ``last_published_version`` instead
            logger.warning(
                "Unable to publish item, not found in published collection.", extra=dict(item_id=request.item_id)
            )

            published_item = published_service.find_one(req=None, item_id=request.item_id, last_published_version=True)
            if not published_item:
                logger.warning(
                    "Published item not found in either ``last_published_version`` or ``_current_version``.",
                    extra=dict(item_id=request.item_id),
                )
            return PublishRequestResponse(routed=False)

        published_item_id = published_item[ID_FIELD]

        if self.polling and published_item.get(QUEUE_STATE) == PublishState.PUSHED:
            # This request will be processed by ``PublishExchangeFactory.send_scheduled_or_pending_content``
            logger.info(f"Setting item {request.item_id} to be polled for later")
            await self.set_published_item_pending(published_item_id)
            return PublishRequestResponse(routed=True)

        try:
            if request.item.get(ITEM_STATE) == CONTENT_STATE.SCHEDULED:
                if (utc_schedule := get_utc_publish_schedule(published_item)) and utc_schedule < utcnow():
                    # This item will be picked up by the ``ExchangeFactory.send_scheduled_or_pending_content`` task
                    # So we respond that the item was routed, i.e. success (for now)
                    return PublishRequestResponse(routed=True)

                await self.updated_scheduled_item(published_item)
            else:
                await self.update_published_item(published_item_id)

            response = await super().send(request)

            if not response.content_api_subscribers and request.publish_to_content_api and content_api.is_enabled():
                try:
                    # If there were no ContentAPI Subscribers, we push it there manually now
                    get_resource_service("content_api").publish(request.item, [])
                except Exception:
                    logger.exception(
                        "Failed to queue item to API",
                        extra=dict(
                            item_id=request.item_id,
                            operation=request.operation,
                        ),
                    )

            # if the item was routed then set the state to "queued"
            # else set the queue state to "queued_not_transmitted"
            queue_state = PublishState.QUEUED if response.routed else PublishState.QUEUED_NOT_TRANSMITTED
            published_service.patch(published_item_id, {QUEUE_STATE: queue_state})

            return response

        except ConnectionTimeout as error:  # recoverable, set state to pending and retry next time
            error_updates = {QUEUE_STATE: PublishState.PENDING, ERROR_MESSAGE: str(error)}
            published_service.patch(published_item_id, error_updates)
            raise
        except SoftTimeLimitExceeded as error:
            # A celery timeout error occurred
            error_updates = {QUEUE_STATE: PublishState.PENDING, ERROR_MESSAGE: str(error)}
            published_service.patch(published_item_id, error_updates)
            raise
        except Exception as error:
            error_updates = {QUEUE_STATE: PublishState.ERROR, ERROR_MESSAGE: str(error)}
            published_service.patch(published_item_id, error_updates)
            raise

    async def set_published_item_pending(self, item_id: ObjectId) -> None:
        """
        Marks a published item as pending by updating its queue state and the timestamp of the last
        queue event in the database. The operation is executed asynchronously.

        :param item_id: The ID of the published item to be updated.
        """

        published_update = {QUEUE_STATE: PublishState.PENDING, "last_queue_event": utcnow()}
        get_resource_service(PUBLISHED).patch(item_id, published_update)

    async def update_published_item(self, item_id: ObjectId):
        """
        Updates the publish state of an item to indicate it is in progress.

        This function updates the state of a specific item in the published database
        to mark it as being published. The `last_queue_event` field is updated to the
        current UTC timestamp to reflect when the transition occurred. It utilizes
        the `get_resource_service` to update the targeted item.

        :param item_id: The ID of the published item to be updated.
        """

        published_update = {QUEUE_STATE: PublishState.IN_PROGRESS, "last_queue_event": utcnow()}
        get_resource_service(PUBLISHED).patch(item_id, published_update)

    async def updated_scheduled_item(self, published_item: dict):
        """
        Updates a scheduled item to published state, modifies its version and related metadata
        in archive and published collections, sends notifications, and triggers related operations.

        :param published_item: Dictionary representing the information of the scheduled item to update,
            including item ID, state, and versioning details.

        Notes
        -----
        - Modifies the `state` of the item from scheduled to published.
        - Updates version metadata in the `archive` and `published` collections.
        - Inserts the modified item version into the appropriate version records.
        - Updates the archive item's history and triggers auxiliary operations like
          import into legal archive and sending content notifications.
        - This function triggers signals for item publication and sends queue events
          for clients to process further.
        - Logging is performed to provide operation updates and trace activities.
        """

        # if scheduled then change the state to published
        # change the `version` and `versioncreated` for the item
        # in archive collection and published collection.

        published_item_id: ObjectId = published_item[ID_FIELD]
        item_id: str = published_item["item_id"]
        archive_service = get_resource_service(ARCHIVE)
        versioncreated = utcnow()
        item_updates = {"versioncreated": versioncreated, ITEM_STATE: CONTENT_STATE.PUBLISHED}
        resolve_document_version(
            document=item_updates,
            resource=ARCHIVE,
            method="PATCH",
            latest_doc={VERSION: published_item.get(VERSION, 1)},
        )

        # update the archive collection
        archive_item = archive_service.find_one(req=None, _id=item_id)
        archive_service.system_update(item_id, item_updates, archive_item)
        # insert into version.
        insert_into_versions(item_id, doc=None)

        # update archive history
        app = get_current_app().as_any()

        app.on_archive_item_updated(item_updates, archive_item, ITEM_PUBLISH)
        # import to legal archive
        await import_into_legal_archive.apply_async(countdown=3, kwargs={"item_id": item_id})
        logger.info(f"Modified the version of scheduled item: {published_item_id}")

        logger.info(f"Publishing scheduled item_id: {published_item_id}")
        # update the published collection
        published_update = {QUEUE_STATE: PublishState.IN_PROGRESS, "last_queue_event": utcnow()}
        published_update.update(item_updates)
        published_item.update(
            {
                "versioncreated": versioncreated,
                ITEM_STATE: CONTENT_STATE.PUBLISHED,
                VERSION: item_updates[VERSION],
            }
        )
        # send a notification to the clients
        push_content_notification([{"_id": str(published_item["item_id"]), "task": published_item.get("task", None)}])
        #  apply internal destinations
        original = archive_service.find_one(req=None, _id=published_item["item_id"])
        signals.item_published.send(
            self,
            item=original,
            after_scheduled=True,
        )
        await signals.item_published_async.send(original, True)
        get_resource_service(PUBLISHED).patch(published_item_id, published_update)
