import logging

from superdesk.types import SubscribersResource, PublishRequest, PublishRequestResponse, ContentState

from ..publish_cache import PublishCache
from ..utils import get_subscribers_for_previously_sent_items
from .content_exchange_filter import ContentPublishExchangeFilter


logger = logging.getLogger(__name__)


class CorrectedPublishExchangeFilter(ContentPublishExchangeFilter):
    """
    CorrectedPublishExchangeFilter class handles filtering subscribers for article corrections.

    This class is a specialized filter for handling articles marked as corrected. Its primary role is
    to determine which subscribers need to receive the corrected article version based on their
    previous subscriptions and various filtering criteria. The process includes checking the
    article's target media type, excluding certain subscribers based on conditions like 'targeted_for'
    property, and applying publish and global filters.
    """

    name: str = "content:corrected"

    async def filter_subscribers(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        """
        Filters the subscribers for the given document based on the specified target_media_type
        for an article correction. This involves identifying eligible subscribers who have
        either previously received the document or are part of the active subscribers list,
        and applying additional filtration based on specific criteria.

        The filtration process is as follows:

        1. Identify subscribers (digital and wire) who previously received the article.
        2. Fetch the list of active subscribers and exclude those who have already received
           the article in the past.
        3. If the article has the property 'targeted_for' (e.g., "target_regions"), exclude
           subscribers of type "Internet" from the active subscribers list.
        4. Further filter the remaining active subscribers by applying publish filters and
           global filters specific to this document.

        :param request: PublishRequest object containing information about the document to
            correct, including its metadata, target media type, and the current state.
        :param response: PublishRequestResponse object that will be populated with the final
            list of filtered subscribers, along with associated product codes and their associations.
        :returns: None. The filtered subscriber list, along with their product codes and associations,
            is set in the `response` object.
            - response.subscribers: A list of filtered subscriber objects.
            - response.subscriber_codes: A dictionary mapping subscribers to their product codes.
            - response.associations: A dictionary of associations for each subscriber.
        """

        # step 1
        query = {
            "item_id": request.item_id,
            "publishing_action": {"$in": [ContentState.PUBLISHED, ContentState.CORRECTED]},
        }

        (
            subscribers,
            subscriber_codes,
            previous_associations,
        ) = await get_subscribers_for_previously_sent_items(response, query)
        subscribers_yet_to_receive: list[SubscribersResource] = []

        if subscribers:
            # Step 2
            cache = PublishCache.get()
            active_subscribers = list(cache.subscribers.values())
            subscribers_yet_to_receive = [
                active_subscriber
                for active_subscriber in active_subscribers
                if not any(active_subscriber.id == previous_subscriber.id for previous_subscriber in subscribers)
            ]

            if len(subscribers_yet_to_receive) > 0:
                # Step 3
                if request.item.get("target_regions"):
                    subscribers_yet_to_receive = SubscribersResource.filter_non_digital(subscribers_yet_to_receive)

                # Step 4
                subscribers_request = PublishRequest(
                    item=request.item,
                    item_id=request.item_id,
                    operation=request.operation,
                    published_state=request.published_state,
                    item_type=request.item_type,
                    target_media_type=request.target_media_type,
                    sender_type=request.sender_type,
                    subscribers=subscribers_yet_to_receive,
                )
                subscribers_response = PublishRequestResponse()
                await super().filter_subscribers(subscribers_request, subscribers_response)

                subscribers_yet_to_receive = subscribers_response.subscribers
                if subscribers_response.subscriber_codes:
                    subscriber_codes.update(subscribers_response.subscriber_codes)
        else:
            logger.info(f"No previous subscribers found for item {request.item_id}")

        response.subscribers = subscribers
        subscriber_ids = set([subscriber.id for subscriber in subscribers])
        for subscriber in subscribers_yet_to_receive:
            if subscriber.id in subscriber_ids:
                continue
            response.subscribers.append(subscriber)
            subscriber_ids.add(subscriber.id)

        response.subscriber_codes = subscriber_codes
        response.associations = await self._filter_subscribers_for_associations(
            request, response, previous_associations
        )
