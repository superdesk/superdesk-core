import logging
from bson import ObjectId

from superdesk.types import (
    PublishRequest,
    PublishRequestResponse,
    ContentState,
    TEXT_TYPES,
    SubscribersResource,
)
from superdesk.resource_fields import ASSOCIATIONS, ID_FIELD, GUID_FIELD, ITEM_TYPE

from ..utils import get_subscribers_for_previously_sent_items
from .base_exchange_filter import BasePublishExchangeFilter


logger = logging.getLogger(__name__)


class ContentPublishExchangeFilter(BasePublishExchangeFilter):
    """
    ContentPublishExchangeFilter is a class responsible for managing the filtering of subscribers during the
    content publishing or updating process. It implements mechanisms to handle both original and rewritten
    content items, ensuring that the appropriate subscribers are targeted based on content status and
    associations.

    This class is utilized as part of a content publishing pipeline to determine which subscribers should be
    updated or notified about content changes. It handles relationships between content items, filtering
    subscribers based on associated content when necessary, and ensures deduplication of subscribers during
    rewrites.
    """

    name: str = "content"

    async def filter_subscribers(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        """
        Filters and processes subscribers based on the status of the item within the request. If the item is a
        rewrite of an existing item, it is processed differently compared to an original item. Modifies the
        response accordingly.

        :param request: The request object containing details about the item to be processed.
        :param response: The response object to be populated with the processed result.
        """

        if request.item.get("rewrite_of"):
            await self._process_rewrite_item(request, response)
        else:
            await self._process_original_item(request, response)

    async def _process_original_item(self, request: PublishRequest, response: PublishRequestResponse):
        """
        Processes the original request item and filters subscribers and associations.

        Summary:
        This method processes the provided request by filtering relevant subscribers
        and their associations. It first invokes the base class's functionality for
        subscriber filtering and then processes specific associations for the response.
        The resulting associations are updated in the response accordingly.

        :param request: The input publish request containing data for subscriber processing.
        :param response: The response object to populate with filtered subscribers and their associations.
        """

        await super().filter_subscribers(request, response)
        response.associations = await self._filter_subscribers_for_associations(request, response)

    async def _process_rewrite_item(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        """
        Processes a rewrite item by fetching relevant subscribers, updating subscriber lists,
        handling codes, and filtering associations for the provided rewrite request.

        :param request: The publish request containing the item and other details of the rewrite process.
        :param response: The response object that will be updated with subscribers, codes, and associations.

        Notes
        -----
        This method first determines if the item in the request is part of a rewrite (based on
        the `rewrite_of` field). If it is, it retrieves the relevant subscribers, codes, and
        associations for the rewritten item. Subsequently, the subscribers in the response
        are filtered and updated accordingly. The method also takes care of merging codes
        and updating associations to reflect the changes caused by the rewrite process.
        Long-standing subscribers and their associations are filtered before finalizing the
        response subscriber list.
        """

        rewrite_of = request.item.get("rewrite_of")

        rewrite_subscribers: list[SubscribersResource] = []
        rewrite_codes: dict[ObjectId, set[str]] = {}
        rewrite_associations: dict[ObjectId | str, list[str]] = {}

        if request.item_type in TEXT_TYPES:
            query = {
                "item_id": rewrite_of,
                "publishing_action": {"$in": [ContentState.PUBLISHED, ContentState.CORRECTED]},
            }

            (
                rewrite_subscribers,
                rewrite_codes,
                rewrite_associations,
            ) = await get_subscribers_for_previously_sent_items(response, query)

            if not rewrite_subscribers:
                logger.info(f"No previous subscribers found for rewrite item: {rewrite_of}")

        await super().filter_subscribers(request, response)

        if rewrite_subscribers:
            subscribers_ids = set(subscriber.id for subscriber in rewrite_subscribers)
            response.subscribers = rewrite_subscribers + [
                subscriber for subscriber in response.subscribers if subscriber.id not in subscribers_ids
            ]

        if rewrite_codes:
            # Join the codes
            response.subscriber_codes.update(rewrite_codes)

        # update associations
        self._update_associations(response.associations, rewrite_associations)

        # handle associations
        response.associations = await self._filter_subscribers_for_associations(
            request, response, response.associations
        )

    def _update_associations(self, original: dict, updates: dict) -> None:
        """
        Updates associations in the original dictionary by merging the provided updates into it.

        This method takes two dictionaries: `original` and `updates`. For each key in
        the `updates` dictionary, it adds or merges the corresponding values into the
        `original` dictionary. If a key does not already exist in the `original`,
        it is added. The merging ensures that the values are unique within the
        resulting collection.

        :param original: The dictionary to update with the new associations.
        :param updates: The dictionary containing new associations to merge.
        """

        if not updates:
            return

        for subscriber, items in updates.items():
            if items:
                original[subscriber] = list(set(original.get(subscriber, [])) | set(updates.get(subscriber, [])))

    async def _filter_subscribers_for_associations(
        self, request: PublishRequest, response: PublishRequestResponse, existing_associations: dict | None = None
    ) -> dict[ObjectId | str, list[str]]:
        """
        Filters and validates subscribers for associated items in a publication request.

        This method processes the associations within the request item, filters the subscribers
        for each associated item based on validation against current and previously published
        subscribers, and returns a mapping of associated item IDs to the list of subscriber IDs.
        Additionally, it considers existing associations if provided.

        :param request: The publication request containing the item and related data.
        :param response: The response object holding the subscribers.
        :param existing_associations: Optional dictionary of existing associations mapping
            subscriber IDs to associated item IDs already published.
        :return: A dictionary where keys are associated item IDs and values are lists of
            validated subscriber IDs for each associated item.
        """

        if not request.item.get(ASSOCIATIONS) or not response.subscribers:
            return {}

        if existing_associations is None:
            existing_associations = {}

        associations: dict[ObjectId | str, list[str]] = {}
        for assoc, item in request.item.get(ASSOCIATIONS, {}).items():
            if not item:
                continue

            assoc_subscribers: set[ObjectId] = set()
            assoc_id = item.get(ID_FIELD) or item.get(GUID_FIELD)

            assoc_request = PublishRequest(
                item=item,
                item_id=assoc_id,
                operation=request.operation,
                published_state=request.published_state,
                item_type=item.get(ITEM_TYPE),
                target_media_type=request.target_media_type,
                sender_type=request.sender_type,
                subscribers=response.subscribers.copy(),
            )
            assoc_response = PublishRequestResponse()
            await super().filter_subscribers(assoc_request, assoc_response)
            for subscriber in assoc_response.subscribers:
                # for the validated subscribers
                subscriber_id = subscriber.id
                if not associations.get(assoc_id):
                    associations[assoc_id] = []

                associations[assoc_id].append(assoc_id)
                assoc_subscribers.add(subscriber_id)

            for subscriber_id, items in existing_associations.items():
                # for the not validated associated item but previously published to the subscriber.
                if assoc_id in items and assoc_id not in associations.get(subscriber_id, []):
                    if not associations.get(subscriber_id):
                        associations[subscriber_id] = []

                    associations[subscriber_id].append(assoc_id)
                    assoc_subscribers.add(subscriber_id)

            request.item["subscribers"] = list(assoc_subscribers)

        return associations
