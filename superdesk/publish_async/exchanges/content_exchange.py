import logging
from copy import deepcopy
from dataclasses import dataclass

from bson import ObjectId
from celery.exceptions import SoftTimeLimitExceeded
from quart_babel import gettext
import elasticapm

# TODO-ASYNC: Replace resolve_document_version with something from async core lib
from eve.versioning import resolve_document_version
from eve.utils import ParsedRequest

from superdesk.core import get_current_app, json
from superdesk.types import (
    PublishRequest,
    PublishRequestResponse,
    PublishState,
    SubscribersResource,
    SubscriberType,
    PublishSenderType,
    PublishOperation,
)
from superdesk import get_resource_service
import superdesk.signals as signals
from superdesk.resource_fields import ID_FIELD, VERSION, ITEM_STATE
from superdesk.metadata.item import CONTENT_STATE, CONTENT_TYPE
from superdesk.errors import ConnectionTimeout, SuperdeskApiError
from superdesk.utc import utcnow

from apps.archive.common import ARCHIVE, insert_into_versions_async
from apps.content import push_content_notification
from superdesk.publish_async.utils import get_utc_publish_schedule, ITEM_PUBLISH, QUEUE_STATE, PUBLISHED, ERROR_MESSAGE
from apps.legal_archive.commands import import_into_legal_archive

import content_api

from ..publish_cache import PublishCache
from ..utils import (
    get_residrefs,
    get_subscribers_for_previously_sent_items,
    remove_ref_from_inmem_package,
    replace_ref_in_package,
)
from ..commands import enqueue_published
from .base_exchange import BasicPublishExchange

logger = logging.getLogger(__name__)


@dataclass
class SubscriberPackageItems:
    subscriber: SubscribersResource
    items: dict[str, str | None]
    codes: set[str]


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
        await PublishCache.init()
        published_service = get_resource_service(PUBLISHED)
        published_item = await self.get_published_item_from_request(request)
        if not published_item:
            return PublishRequestResponse(routed=False)

        published_item_id = ObjectId(published_item[ID_FIELD])

        if self.polling and published_item.get(QUEUE_STATE) == PublishState.PUSHED:
            # This request will be processed by ``PublishExchangeFactory.send_scheduled_or_pending_content``
            logger.info(f"Setting item {request.item_id} to be polled for later")
            await self.set_published_item_pending(published_item_id)
            if request.sender_type == PublishSenderType.API:
                # If this request was from the API, then run the celery task now
                # otherwise this task can wait for the next polling iteration
                await enqueue_published.apply_async()
            return PublishRequestResponse(routed=True)

        try:
            if request.item.get(ITEM_STATE) == CONTENT_STATE.SCHEDULED:
                if (utc_schedule := get_utc_publish_schedule(published_item)) and utc_schedule > utcnow():
                    # This item will be picked up by the ``ExchangeFactory.send_scheduled_or_pending_content`` task
                    # So we respond that the item was routed, i.e. success (for now)
                    if published_item.get(QUEUE_STATE) != PublishState.PENDING:
                        # Make sure to set the ``published`` item queue state to pending, so it is picked up later
                        await self.set_published_item_pending(published_item_id)
                    return PublishRequestResponse(routed=True)

                await self.updated_scheduled_item(published_item)
            else:
                await self.update_published_item(published_item_id)

            request.item = published_item
            response = await self._publish_item(request)

            if not response.content_api_subscribers and request.publish_to_content_api and content_api.is_enabled():
                try:
                    # If there were no ContentAPI Subscribers, we push it there manually now
                    await get_resource_service("content_api").publish_async(request.item, [])
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
            await published_service.patch_async(published_item_id, {QUEUE_STATE: queue_state})

            return response

        except ConnectionTimeout as error:  # recoverable, set state to pending and retry next time
            error_updates = {QUEUE_STATE: PublishState.PENDING, ERROR_MESSAGE: str(error)}
            await published_service.patch_async(published_item_id, error_updates)
            raise
        except SoftTimeLimitExceeded as error:
            # A celery timeout error occurred
            error_updates = {QUEUE_STATE: PublishState.PENDING, ERROR_MESSAGE: str(error)}
            await published_service.patch_async(published_item_id, error_updates)
            raise
        except Exception as error:
            if isinstance(error, KeyError):
                error_msg = gettext(f"Key is missing on article to be published: {error}")
            else:
                error_msg = str(error)
            error_updates = {QUEUE_STATE: PublishState.ERROR, ERROR_MESSAGE: error_msg}
            await published_service.patch_async(published_item_id, error_updates)
            raise

    async def get_published_item_from_request(self, request: PublishRequest) -> dict | None:
        """
        Retrieve the published item associated with the given request.

        This method attempts to fetch a published item from a resource service based on
        the ID and version in the provided request. If the item is not found using the
        current version, the method makes a secondary attempt to locate it using the
        'last_published_version'. If the item cannot be retrieved on either attempt, `None`
        is returned, and appropriate warnings are logged.

        :param request: The request containing the item ID and version details needed to retrieve the published item.
        :return: The retrieved published item if found, otherwise ``None``.
        """

        published_service = get_resource_service(PUBLISHED)

        published_item = await published_service.find_one_async(
            req=None, item_id=request.item_id, _current_version=request.item[VERSION]
        )

        if not published_item:
            # If we failed to get the item by ``_current_version``, then try ``last_published_version`` instead
            logger.warning(
                "Unable to publish item, not found in published collection.", extra=dict(item_id=request.item_id)
            )

            published_item = await published_service.find_one_async(
                req=None, item_id=request.item_id, last_published_version=True
            )

        if not published_item:
            logger.warning(
                "Published item not found in either ``last_published_version`` or ``_current_version``.",
                extra=dict(item_id=request.item_id),
            )

        return published_item

    async def _publish_item(self, request: PublishRequest) -> PublishRequestResponse:
        response: PublishRequestResponse | None = None

        if request.item_type == CONTENT_TYPE.COMPOSITE:
            response = await self._publish_package_items(request)
            if not response:
                # this was only published to subscribers with config.packaged on
                request.target_media_type = SubscriberType.DIGITAL

        return response if response else await super().send(request)

    async def set_published_item_pending(self, item_id: ObjectId) -> None:
        """
        Marks a published item as pending by updating its queue state and the timestamp of the last
        queue event in the database. The operation is executed asynchronously.

        :param item_id: The ID of the published item to be updated.
        """

        published_update = {QUEUE_STATE: PublishState.PENDING, "last_queue_event": utcnow()}
        await get_resource_service(PUBLISHED).patch_async(item_id, published_update)

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
        await get_resource_service(PUBLISHED).patch_async(item_id, published_update)

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
        archive_item = await archive_service.find_one_async(req=None, _id=item_id)
        await archive_service.system_update_async(item_id, item_updates, archive_item)
        # insert into version.
        await insert_into_versions_async(item_id, doc=None)

        # update archive history
        app = get_current_app().as_any()

        await app.on_archive_item_updated.call_async(item_updates, archive_item, ITEM_PUBLISH)
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
        await get_resource_service(PUBLISHED).patch_async(published_item_id, published_update)

    @elasticapm.capture_span()
    async def _publish_package_items(self, request: PublishRequest) -> PublishRequestResponse | None:
        items = get_residrefs(request.item)
        subscriber_items: dict[ObjectId, SubscriberPackageItems] = {}
        removed_items: list[str] = []

        if request.operation in [PublishOperation.CORRECT, PublishOperation.KILL]:
            removed_items, added_items = await self._get_package_changed_items(items, request.item)
            # we raise error if correction is done on a empty package. Kill is fine.
            if (
                len(removed_items) == len(items)
                and len(added_items) == 0
                and request.operation == PublishOperation.CORRECT
            ):
                raise SuperdeskApiError.badRequestError(gettext("Corrected package cannot be empty!"))
            items.extend(added_items)

        if not items:
            return None

        archive_service = get_resource_service("archive")
        for guid in items:
            package_item = await archive_service.find_one_async(req=None, _id=guid)
            if not package_item:
                raise SuperdeskApiError.badRequestError(
                    gettext(f"Package item with id: {guid} has not been published.")
                )

            subscribers, subscriber_codes, associations = await self._get_subscribers_for_package_item(package_item)
            package_item_id = package_item[ID_FIELD]
            self._extend_subscriber_items(
                subscriber_items, subscribers, package_item, package_item_id, subscriber_codes
            )

        for removed_id in removed_items:
            package_item = await archive_service.find_one_async(req=None, _id=removed_id)
            subscribers, subscriber_codes, associations = await self._get_subscribers_for_package_item(package_item)
            package_item_id = None
            self._extend_subscriber_items(
                subscriber_items, subscribers, package_item, package_item_id, subscriber_codes
            )

        return await self.publish_package(request, subscriber_items)

    @elasticapm.capture_span()
    async def publish_package(
        self, request: PublishRequest, target_subscribers: dict[ObjectId, SubscriberPackageItems]
    ) -> PublishRequestResponse | None:
        """Publishes a given package to given subscribers.

        For each subscriber updates the package definition with the wanted_items for that subscriber
        and removes unwanted_items that doesn't supposed to go that subscriber.
        Text stories are replaced by the digital versions.

        :param request: The publication request containing the details for publishing.
        :param target_subscribers: Dictionary of Subscriber ID and items-per-subscriber
        :return: PublishRequestResponse if the request was handled, else ``None``.
        """

        all_items = get_residrefs(request.item)
        response = PublishRequestResponse()
        for items in target_subscribers.values():
            sub_request = deepcopy(request)
            subscriber = items.subscriber
            codes = items.codes
            wanted_items: list[str] = [item_id for item_id, package_id in items.items.items() if package_id]
            unwanted_items: list[str] = [item for item in all_items if item not in wanted_items]

            for i in unwanted_items:
                still_items_left = remove_ref_from_inmem_package(sub_request.item, i)
                if not still_items_left and request.operation != PublishOperation.CORRECT:
                    # if nothing left in the package to be published and
                    # if not correcting then don't send the package
                    return None

            for key in wanted_items:
                try:
                    await replace_ref_in_package(sub_request.item, key, items.items[key])
                except KeyError:
                    continue

            single_publish_response = PublishRequestResponse(
                subscribers=[subscriber],
                subscriber_codes={subscriber.id: codes},
            )
            tasks, no_formatters = await self.get_tasks(sub_request, single_publish_response)
            # Store this exchange config with all the Tasks,
            # So it can be used in future to retrieve the exchange that manages this task
            exchange_config = self.get_exchange_config()
            for task in tasks:
                task.exchange = exchange_config

            self._push_formatter_notification(sub_request, no_formatters)
            await self.route_tasks(sub_request, single_publish_response, tasks)

            if single_publish_response.routed:
                response.routed = True
                response.subscribers.extend(single_publish_response.subscribers)
                response.content_api_subscribers |= single_publish_response.content_api_subscribers
                response.subscriber_codes.update(single_publish_response.subscriber_codes)

        return None if not response.routed else response

    async def _get_package_changed_items(self, existing_items: list[str], package: dict) -> tuple[list[str], list[str]]:
        """Returns the added and removed items from existing_items

        :param existing_items: List of item IDs that currently exist on the package
        :param package: The package to check for changes
        :return: A tuple containing the item IDs for those removed and added
        """

        published_service = get_resource_service("published")
        req = ParsedRequest()
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"terms": {QUEUE_STATE: [PublishState.QUEUED, PublishState.QUEUED_NOT_TRANSMITTED]}},
                            {"term": {"item_id": package["item_id"]}},
                        ]
                    }
                }
            },
            "sort": [{"publish_sequence_no": "desc"}],
        }
        req.args = {"source": json.dumps(query)}
        req.max_results = 1
        previously_published_packages = await published_service.get_async(req=req, lookup=None)

        try:
            previously_published_package = await previously_published_packages.next()
        except StopAsyncIteration:
            previously_published_package = None

        if not previously_published_package:
            return [], []

        if "groups" in previously_published_package:
            old_items = get_residrefs(previously_published_package)
            added_items = list(set(existing_items) - set(old_items))
            removed_items = list(set(old_items) - set(existing_items))
            return removed_items, added_items
        else:
            return [], []

    async def _get_subscribers_for_package_item(
        self, package_item: dict
    ) -> tuple[list[SubscribersResource], dict[ObjectId, set[str]], dict[ObjectId | str, list[str]]]:
        """Finds the list of subscribers for a given item in a package

        :param package_item: item in a package
        :return: A tuple containing the following:
            - ``list[SubscribersResource]``: List of active subscribers matching the criteria.
            - ``dict[ObjectId, set[str]]``: Mapping of subscriber IDs to their unique codes.
            - ``dict[ObjectId | str, list[str]]``: Mapping of subscriber IDs to associated items.
        """

        query = {"$and": [{"item_id": package_item[ID_FIELD]}, {"publishing_action": package_item[ITEM_STATE]}]}
        return await get_subscribers_for_previously_sent_items(PublishRequestResponse(), query)

    def _extend_subscriber_items(
        self,
        subscriber_items: dict[ObjectId, SubscriberPackageItems],
        subscribers: list[SubscribersResource],
        item: dict,
        package_item_id: str | None,
        subscriber_codes: dict[ObjectId, set[str]],
    ):
        """Extends the subscriber_items with the given list of subscribers for the item

        :param subscriber_items: The existing list of subscribers
        :param subscribers: New subscribers that item has been published to - to be added
        :param item: item that has been published
        :param package_item_id: package_item_id
        :param subscriber_codes: Mapping of subscriber IDs to their configured codes
        """

        item_id = item[ID_FIELD]
        for subscriber in subscribers:
            item_list = subscriber_items[subscriber.id].items if subscriber.id in subscriber_items else {}
            item_list[item_id] = package_item_id
            subscriber_items[subscriber.id] = SubscriberPackageItems(
                subscriber=subscriber,
                items=item_list,
                codes=subscriber_codes.get(subscriber.id, set()),
            )
