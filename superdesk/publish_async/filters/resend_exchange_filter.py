from superdesk.types import SubscribersResource, PublishRequest, ProductsResource

from .base_exchange_filter import BasePublishExchangeFilter


class ResendPublishExchangeFilter(BasePublishExchangeFilter):
    """
    Represents a filter that determines subscriber and product eligibility
    for resend operations in a publish-subscribe system.

    This filter is specialized for resend operations and bypasses certain
    checks that are typically enforced in other types of operations.
    It ensures that the appropriate subscribers and products are selected
    for publication without validating specific attributes like type or
    target during the resend process.
    """

    name: str = "resend"

    async def get_subscribers(self, request: PublishRequest) -> list[SubscribersResource]:
        """
        Returns the list of subscribers provided in the publish request.

        :param request: The publish request containing the subscribers information.
        :return: The list of subscribers extracted from the publish request, or an empty list if none are available.
        """

        return request.subscribers or []

    def subscriber_type_matches_request_type(self, request: PublishRequest, subscriber: SubscribersResource) -> bool:
        """
        When resending an article, skip checking subscriber type against request type.

        :param request: The publish request containing the subscriber type.
        :param subscriber: The subscriber resource containing the subscriber type.
        :return: ``True``
        """

        return True

    def subscriber_target_matches_item_target(self, request: PublishRequest, subscriber: SubscribersResource) -> bool:
        """
        When resending an article, skip checking subscriber target against item target.

        :param request: The publish request containing the subscriber type.
        :param subscriber: The subscriber resource containing the subscriber type.
        :return: ``True``
        """

        return True

    def cache_global_filter_matches(self, request: PublishRequest):
        """
        When resending an article, skip checking global filters.

        :param request: The publish request containing the subscriber type.
        """

        pass

    def subscriber_matches_global_filter(self, subscriber: SubscribersResource) -> bool:
        """
        When resending an article, skip checking subscriber against global filter.

        :param subscriber: The subscriber resource containing the product details.
        :return: ``True``
        """

        return True

    def product_matches_item(self, request: PublishRequest, product: ProductsResource) -> bool:
        """
        When resending an article, skip checking Product matches item.

        :param request: The publish request containing the subscriber type.
        :param product: The product resource containing the product details.
        :return: ``True``
        """

        return True
