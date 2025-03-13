import logging
from itertools import chain

from bson import ObjectId
import elasticapm
from quart_babel import gettext

from superdesk.types import (
    PublishExchangeFilter,
    SubscribersResource,
    SubscriberType,
    PublishRequest,
    PublishRequestResponse,
    ProductsResource,
    ProductFilterType,
    ContentFiltersResource,
    ContentType,
)

from superdesk.errors import SuperdeskApiError
from superdesk.publish_async.publish_cache import PublishCache

from apps.content_filters.filter_condition.filter_condition import FilterCondition

import content_api

from ..utils import get_codes, is_doc_targeted


logger = logging.getLogger(__name__)


class BasePublishExchangeFilter(PublishExchangeFilter):
    """
    BasePublishExchangeFilter is responsible for filtering subscribers, matching content to subscribers’ configurations,
    and processing the details for content-targeted publishing.

    The class extends PublishExchangeFilter and provides functionality to apply global and
    specific filters on subscribers, process products, and manage the association of matched products with subscribers.
    It determines the subscribers for a publish request based on filtering criteria such as
    subscriber types, targets, global content filters, and product characteristics.
    """

    name: str = "default"

    async def filter_subscribers(self, request: PublishRequest, response: PublishRequestResponse) -> None:
        """
        Filters subscribers based on the given publish request. This method updates the
        global filter matches, retrieves subscribers fulfilling the criteria, processes
        the products for these subscribers, and handles individual subscriber actions.
        If no subscribers are found for the request, a warning is logged.

        :param request: The PublishRequest instance with details for filtering subscribers and products.
        :param response: The PublishRequestResponse instance for collecting the filtering results.
        """

        self.cache_global_filter_matches(request)
        subscribers = await self.get_subscribers(request)
        self.process_products(request, response, subscribers)
        for subscriber in subscribers:
            self.process_subscriber(request, response, subscriber)

        if not response.subscribers:
            logger.warning(f"No subscribers found for {request.item.get('id')}")
            return

    async def get_subscribers(self, request: PublishRequest) -> list[SubscribersResource]:
        """
        Retrieve matching subscribers for a given publish request.

        This method filters cached subscribers based on the criteria defined in
        the helper methods `subscriber_type_matches_request_type` and
        `subscriber_target_matches_item_target`. It retrieves the subscribers from
        a cached instance of `PublishCache` and applies the filtering logic to return
        a list of relevant subscribers for the publish request.

        :param request: The PublishRequest instance with details for filtering subscribers and products.
        :return: A list of Subscribers to use for checking against this publish request.
        """

        cache = PublishCache.get()
        return [
            subscriber
            for subscriber in cache.subscribers.values()
            if (
                self.subscriber_type_matches_request_type(request, subscriber)
                and self.subscriber_target_matches_item_target(request, subscriber)
            )
        ]

    def process_products(
        self, request: PublishRequest, response: PublishRequestResponse, subscribers: list[SubscribersResource]
    ) -> None:
        """
        Processes products and Content API products based on the provided request and the list of subscribers.

        This method determines the set of product IDs and API product IDs from the given subscribers,
        matches them to the request, and populates the response with the matched products,
        matched API products, and their corresponding product codes.

        :param request: The PublishRequest instance with details for filtering subscribers and products.
        :param response: The response object to hold matched products, API products, and their product codes.
        :param subscribers: A list of subscriber resources contributing to the product and API product IDs.
        """

        product_ids: set[ObjectId] = set(
            chain(*[subscriber.products for subscriber in subscribers if subscriber.products])
        )
        api_product_ids: set[ObjectId] = (
            set()
            if not request.publish_to_content_api or not content_api.is_enabled()
            else set(chain(*[subscriber.api_products for subscriber in subscribers if subscriber.api_products]))
        )

        response.matched_products = self.get_matching_products(request, product_ids)
        response.matched_api_products = self.get_matching_products(request, api_product_ids)
        response.product_codes = {
            product.id: get_codes(product) for product in response.matched_products + response.matched_api_products
        }

    def process_subscriber(
        self, request: PublishRequest, response: PublishRequestResponse, subscriber: SubscribersResource
    ) -> None:
        """
        Processes a subscriber and determines their inclusion in the response based
        on specified conditions. The function evaluates the subscriber's products and
        API products, checking for matches to include them in the response.
        Additionally, targeted subscribers are considered for inclusion even if
        they do not match product criteria.

        :param request: The PublishRequest instance with details for filtering subscribers and products.
        :param response: The response object to hold matched products, API products, and their product codes.
        :param subscriber: The subscriber being evaluated for inclusion in the response.
        """

        subscriber_added = False
        subscriber_codes = get_codes(subscriber)

        products_match, product_codes = self.get_matched_subscriber_products_codes(response, subscriber.products or [])
        if products_match:
            subscriber_added = True
            response.subscribers.append(subscriber)
            subscriber_codes.update(product_codes)

        products_match, product_codes = self.get_matched_subscriber_products_codes(
            response, subscriber.api_products or [], use_api_products=True
        )
        if products_match:
            if not subscriber_added:
                subscriber_added = True
                response.subscribers.append(subscriber)

            response.content_api_subscribers.add(subscriber.id)
            subscriber_codes.update(product_codes)

        if not subscriber_added and self.subscriber_is_targeted(request, subscriber):
            # if targeted subscriber and has api products then send it to api.
            if subscriber.api_products:
                response.content_api_subscribers.add(subscriber.id)
            response.subscribers.append(subscriber)
            subscriber_added = True

        if subscriber_added:
            response.subscriber_codes[subscriber.id] = subscriber_codes

    def get_matched_subscriber_products_codes(
        self, response: PublishRequestResponse, product_ids: list[ObjectId], use_api_products: bool = False
    ) -> tuple[bool, set[str]]:
        """
        Gets the matched subscriber products codes based on the response and a list of
        product IDs. Optionally, it determines whether to use the Content API products or the
        matched products from the response.

        :param response: The response containing matched products and product codes mappings.
        :param product_ids: A list of product IDs to filter the matched products.
        :param use_api_products: If set to ``True``, uses the matched Content API products
            instead of the default matched products from the response. Default is ``False``.
        :return: The first element indicates whether matched product codes exist,
            and the second is a set of matched product codes.
        """

        products = response.matched_api_products if use_api_products else response.matched_products
        matched_products = [product for product in products if product_ids and product.id in product_ids]
        if not len(matched_products):
            return False, set()

        return True, set(
            chain(
                *[
                    response.product_codes[product.id]
                    for product in matched_products
                    if response.product_codes.get(product.id)
                ]
            )
        )

    def subscriber_type_matches_request_type(self, request: PublishRequest, subscriber: SubscribersResource) -> bool:
        """
        Determines whether the subscriber's type is compatible with the request's
        target media type and item type.

        The function checks the compatibility of a request's target media type and
        item type with the subscriber's type. It ensures that subscribers receive
        appropriate content types according to their subscription type. For
        example, a WIRE subscriber may only receive text or preformatted content.

        :param request: A request containing the target media type and item type to be
            matched against the subscriber's type.
        :param subscriber: The subscriber's resource, which includes subscription type indicating
            the allowed content types.
        :return: ``True`` if the subscriber's type matches the request type, ``False`` otherwise.
        """

        if request.target_media_type and subscriber.subscriber_type != SubscriberType.ALL:
            can_send_digital = subscriber.subscriber_type == SubscriberType.DIGITAL
            if (request.target_media_type == SubscriberType.WIRE and can_send_digital) or (
                request.target_media_type == SubscriberType.DIGITAL and not can_send_digital
            ):
                return False
        elif (
            request.item_type not in [ContentType.TEXT, ContentType.PREFORMATTED]
            and subscriber.subscriber_type == SubscriberType.WIRE
        ):
            # wire subscribers can get only text and preformatted stories
            return False

        return True

    def subscriber_target_matches_item_target(self, request: PublishRequest, subscriber: SubscribersResource) -> bool:
        """
        Determines if a subscriber matches the targeting parameters defined in the item's targets.

        The method evaluates if the given subscriber conforms to the targeting conditions specified
        in the item's "target_subscribers", "target_types", and "target_regions". It checks the
        subscriber's identifier, type compatibility, and other targeting rules allowing for a match.

        :param request: The request containing the item's targeting data.
        :param subscriber: The subscriber resource to evaluate against the targets.
        :return: ``True`` if the subscriber matches the targeting constraints, otherwise ``False``.
        """

        # If not targeted at all then Return ``True``
        if not is_doc_targeted(request.item, "target_subscribers") and not is_doc_targeted(
            request.item, "target_types"
        ):
            return True

        for t in request.item.get("target_subscribers", []):
            if str(t.get("_id")) == str(subscriber.id):
                return True

        if subscriber.subscriber_type:
            for t in request.item.get("target_types", []):
                if t["qcode"] == subscriber.subscriber_type and t["allow"]:
                    return True
                if t["qcode"] != subscriber.subscriber_type and not t["allow"]:
                    return True

        # If there's a region target then continue with the subscriber to check products
        if is_doc_targeted(request.item, "target_regions"):
            return True

        # Nothing matches so this subscriber doesn't conform
        return False

    def subscriber_is_targeted(self, request: PublishRequest, subscriber: SubscribersResource) -> bool:
        """
        Determines if the subscriber is targeted based on the requested item's target
        subscribers. Iterates through the `target_subscribers` list within the provided
        PublishRequest and checks if the `subscriber.id` matches any of the targeted
        subscriber IDs.

        :param request: The PublishRequest object containing the item and the target
        :param subscriber: The Subscriber object to verify against the target subscribers.
        :return: ``True`` if the subscriber is targeted, otherwise ``False``.
        """

        for targeted_subscriber in request.item.get("target_subscribers", []):
            if str(targeted_subscriber.get("_id")) == str(subscriber.id):
                return True

        return False

    def subscriber_matches_global_filter(self, subscriber: SubscribersResource) -> bool:
        """
        Determines if a subscriber matches the global content filter criteria.

        This function evaluates whether a given subscriber aligns with the global
        content filters by leveraging cached data. If any global content filter
        disqualifies the subscriber, the function will return ``False``.

        :param subscriber: The subscriber object to be evaluated against the global content filters.
        :return: ``True`` if the subscriber matches the criteria of the global content filters, otherwise ``False``.
        """

        publish_cache = PublishCache.get()

        for global_filter in publish_cache.global_content_filters:
            if (subscriber.global_filters or {}).get(str(global_filter.id)) is not False:
                # Global filter applies to this subscriber
                if publish_cache.global_filter_matches.get(global_filter.id):
                    return False

        return True

    def product_target_matches_item_target(self, request: PublishRequest, product: ProductsResource) -> bool:
        """
        Determines if the target regions of a product match the target regions of an item.

        This function evaluates the geo-restrictions associated with a product and an item's
        target regions to determine if they are consistent. It checks whether the product's
        geo-restriction aligns with the "allow" or "disallow" state of target regions defined
        in the item.

        :param request: The request containing the item with its target regions.
        :param product: The product containing geo-restriction information.
        :return: ``True`` if the product's geo-restrictions match the target regions of the item; ``False`` otherwise.
        """

        if not is_doc_targeted(request.item, "target_regions"):
            return product.geo_restrictions is None
        elif product.geo_restrictions:
            for region in request.item.get("target_regions", []):
                if region["qcode"] == product.geo_restrictions and region["allow"]:
                    return True
                elif region["qcode"] != product.geo_restrictions and not region["allow"]:
                    return True

        return False

    def content_filter_matches_item(
        self, request: PublishRequest, content_filter: ContentFiltersResource | None
    ) -> bool:
        """
        Determines whether a content filter matches a specific item based on the given
        request. The function either uses a cached result or computes the match if no
        cached value is present.

        This method first checks if a content filter is provided. If not, it assumes
        all content filters match the item. Otherwise, it retrieves a cached result or
        evaluates the match using the given content filter and stores the result in the
        cache for future requests.

        :param request: The PublishRequest object containing the item to be evaluated.
        :param content_filter: The content filter to be matched against the item.
            If None, all content filters are treated as matching.
        :return: ``True`` if the content filter matches the item, ``False`` otherwise.
        """

        if not content_filter:
            return True

        cache = PublishCache.get()
        cache_id = cache.generate_cache_id(
            "filter-match", str(content_filter.id) or content_filter.name, request.item_id
        )
        if cache_id not in cache.filter_result_cache:
            cache.filter_result_cache[cache_id] = self._check_item_matches_content_filter(request, content_filter)

        return cache.filter_result_cache[cache_id]

    def _check_item_matches_content_filter(
        self, request: PublishRequest, content_filter: ContentFiltersResource
    ) -> bool:
        """
        Checks if the item matches the criteria defined in a content filter.

        The function evaluates whether an item being published meets the conditions specified in the given
        content filter. It processes multiple filter expressions and checks if they satisfy the conditions
        based on filter conditions or content filter identifiers. If no filters are provided, it returns ``False``.

        :param request: The PublishRequest object containing the item to be evaluated.
        :param content_filter: The content filter resource defining filter expressions and conditions to be matched.
        :return: ``True`` if the item matches any condition in the content filters, otherwise ``False``.
        """

        if not content_filter.content_filter:
            return False

        for index, expression in enumerate(content_filter.content_filter):
            if not expression.expression:
                raise SuperdeskApiError.badRequestError(
                    gettext("Filter statement {index} does not have a filter condition").format(index=index + 1)
                )

            if expression.expression.fc:
                if not self.filter_condition_matches_item(request, content_filter, expression.expression.fc):
                    continue
            if expression.expression.pf:
                if not self.content_filter_ids_matches_item(request, expression.expression.pf):
                    continue

            return True

        return False

    def filter_condition_matches_item(
        self, request: PublishRequest, content_filter: ContentFiltersResource, filter_condition_ids: list[ObjectId]
    ) -> bool:
        """
        Determines whether all specified filter conditions match the given item in the publish request.

        This method evaluates a list of filter conditions against a provided item from the request. It utilizes
        a caching mechanism to avoid redundant processing of the filter conditions that have already been evaluated
        for the same request item. The method returns ``True`` only if all specified filter conditions match the item.
        If any filter condition fails to match, the method immediately returns ``False``.

        :param request: The publish request containing the item to check against the filter conditions.
        :param content_filter: The content filter resource that contains filter conditions to evaluate.
        :param filter_condition_ids: A list of unique identifiers corresponding to the filter conditions to be checked.
        :return: ``True`` if all specified filter conditions match the item in the request. Otherwise, returns ``False``.
        """

        cache = PublishCache.get()
        for filter_condition_id in filter_condition_ids:
            cache_id = cache.generate_cache_id("filter-condition-match", str(filter_condition_id), request.item_id)
            if cache_id not in cache.filter_result_cache:
                filter_condition_item = cache.filter_conditions.get(filter_condition_id)
                if not filter_condition_item:
                    logger.error(
                        f"Missing filter condition {filter_condition_id} in content filter {content_filter.name}"
                    )
                    return False

                filter_condition = FilterCondition.parse(filter_condition_item.to_dict())
                cache.filter_result_cache[cache_id] = filter_condition.does_match(request.item)

            if cache.filter_result_cache[cache_id] is False:
                return False

        return True

    def content_filter_ids_matches_item(self, request: PublishRequest, content_filter_ids: list[ObjectId]) -> bool:
        """
        Determines if a given request's item matches all provided content filter IDs.

        This method evaluates a set of content filter IDs against an item's `PublishRequest`.
        It utilizes a caching mechanism to store and retrieve content filter match results,
        thus reducing redundant computations. A content filter mismatch for any single ID
        results in a ``False`` return immediately. All content filters must return ``True`` for
        the method to confirm a match.

        :param request: The request object containing the item to be evaluated.
        :param content_filter_ids: A list of content filter identifiers to check against the given item.
        :return: ``True`` if all provided content filter IDs match the item, otherwise ``False``.
        """

        cache = PublishCache.get()
        for content_filter_id in content_filter_ids:
            cache_id = cache.generate_cache_id("content-filter-match", str(content_filter_id), request.item_id)
            if cache_id not in cache.filter_result_cache:
                content_filter = cache.content_filters.get(content_filter_id)
                cache.filter_result_cache[cache_id] = self.content_filter_matches_item(request, content_filter)

            if cache.filter_result_cache[cache_id] is False:
                return False

        return True

    def product_filter_matches_item(self, request: PublishRequest, product: ProductsResource) -> bool:
        """
        Determines whether a product filter matches an item based on the request and product's content filter.

        This method evaluates the given product's content filter against the provided request to determine if the
        filter matches. The outcome depends on the type of the product's content filter and the match result.
        If the filter is not specified or lacks a valid filter ID, it is considered a match.

        :param request: The request object used for evaluating the content filter.
        :param product: The resource representing the product, which includes content filter information.
        :return:
            - ``True`` if there's no filter
            - ``True`` if matches and permitting
            - ``False`` if matches and blocking
            - ``False`` if doesn't match and permitting
            - ``True`` if doesn't match and blocking
        """

        if product.content_filter is None or product.content_filter.filter_id is None:
            return True

        publish_cache = PublishCache.get()
        content_filter = publish_cache.content_filters.get(product.content_filter.filter_id)
        does_match = self.content_filter_matches_item(request, content_filter)

        if does_match:
            return product.content_filter.filter_type == ProductFilterType.PERMITTING
        else:
            return product.content_filter.filter_type == ProductFilterType.BLOCKING

    def get_matching_products(self, request: PublishRequest, product_ids: set[ObjectId]) -> list[ProductsResource]:
        """
        Fetches and returns a list of product resources that match the given request criteria from
        the specified set of product IDs. The matching operation utilizes a predefined cache
        to optimize performance and avoid redundant computations.

        :param request: The request object containing the criteria to match products against.
        :param product_ids: A set containing product IDs to be checked for matching.
        :return: A list of product resources that match the request criteria.
            Returns an empty list if no product_ids are provided or no matches are found.
        """

        if not product_ids:
            return []

        with elasticapm.capture_span("check products"):
            cache = PublishCache.get()
            return [
                cache.products[product_id]
                for product_id in product_ids
                if cache.products.get(product_id) and self.product_matches_item(request, cache.products[product_id])
            ]

    def product_matches_item(self, request: PublishRequest, product: ProductsResource) -> bool:
        """
        Determines if a product matches specific criteria in the request.

        This method checks whether the product's targeting matches the item targeting
        and if the product's filter matches the item according to the given request
        and product resource.

        :param request: Contains details of the publishing request such as targeting and filter data.
        :param product: Represents the resource of the product, providing necessary information
            for matching against request details.
        :return: ``True`` if the product matches the targeting and filter criteria
            specified in the request, otherwise ``False``.
        """

        return self.product_target_matches_item_target(request, product) and self.product_filter_matches_item(
            request, product
        )

    def cache_global_filter_matches(self, request: PublishRequest):
        """
        Caches the global filter matches for a given publish request. This method processes
        the global filters stored in the PublishCache, evaluates matches based on content
        filters, and stores the results in the cache for efficient reuse.

        :param request: The request object containing the necessary information to
            evaluate content filter matches for global filters.
        """

        cache = PublishCache.get()
        cache.global_filter_matches = {
            global_filter.id: self.content_filter_matches_item(request, global_filter)
            for global_filter in cache.global_content_filters
        }
