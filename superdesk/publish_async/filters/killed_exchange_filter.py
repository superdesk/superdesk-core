from superdesk.core import get_config
from superdesk.types import PublishRequest, PublishRequestResponse, ContentState

from ..utils import get_codes, get_subscribers_for_previously_sent_items
from .content_exchange_filter import ContentPublishExchangeFilter


class KilledPublishExchangeFilter(ContentPublishExchangeFilter):
    """
    KilledPublishExchangeFilter processes publication requests by filtering subscribers based
    on the target media type and the document's state. It ensures that a kill operation is sent
    to subscribers who have previously received the document, either in its published or corrected state.

    This class is derived from ContentPublishExchangeFilter and provides additional filtering logic
    specific to handling "killed" publications. It is primarily used for managing unpublishing actions
    to the correct set of subscribers.
    """

    name: str = "content:killed"

    async def filter_subscribers(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        """
        Filters subscribers to receive a "kill" operation for a document.

        This method determines the subscribers to notify when a document is "killed".
        It targets all subscribers who previously received the document
        in its "published" or "corrected" states. If no prior subscribers are found,
        the method may optionally re-filter based on configuration.

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

        query = {
            "$and": [
                {"item_id": request.item_id},
                {"publishing_action": {"$in": [ContentState.PUBLISHED, ContentState.CORRECTED]}},
            ]
        }
        (
            previous_subscribers,
            subscriber_codes,
            previous_associations,
        ) = await get_subscribers_for_previously_sent_items(response, query)

        if not previous_subscribers and get_config(bool, "UNPUBLISH_TO_MATCHING_SUBSCRIBERS", False):
            subscribers_request = PublishRequest(
                item=request.item,
                item_id=request.item_id,
                operation=request.operation,
                published_state=request.published_state,
                item_type=request.item_type,
                target_media_type=request.target_media_type,
                sender_type=request.sender_type,
            )
            subscribers_response = PublishRequestResponse()
            await super().filter_subscribers(subscribers_request, subscribers_response)
            previous_subscribers = subscribers_response.subscribers
            subscriber_codes = subscribers_response.subscriber_codes

        response.subscribers = previous_subscribers
        response.subscriber_codes = subscriber_codes

        # Check to see if any provided Subscribers in the PublishRequest were not picked up by the above
        # logic. If so then add them to the list, along with their subscriber codes
        previous_subscriber_ids = set([subscriber.id for subscriber in previous_subscribers])
        new_subscribers = [
            subscriber for subscriber in request.subscribers or [] if subscriber.id not in previous_subscriber_ids
        ]
        if new_subscribers:
            response.subscribers.extend(new_subscribers)
            for subscriber in new_subscribers:
                response.subscriber_codes[subscriber.id] = get_codes(subscriber)

        response.associations = previous_associations
        response.content_api_subscribers = set(
            [subscriber.id for subscriber in response.subscribers if subscriber.api_products]
        )
