from typing import Any
import logging

from bson import ObjectId
from quart_babel import gettext

from superdesk.core.resources import AsyncResourceService

from superdesk import get_resource_service
from superdesk.types import ContentFiltersResource, SubscribersResource, ProductsResource
from superdesk.errors import SuperdeskApiError

from .utils import _get_content_filters_by_content_filter


logger = logging.getLogger(__name__)


class ContentFiltersService(AsyncResourceService[ContentFiltersResource]):
    async def update(
        self,
        item_id: ObjectId | str,
        updates: dict[str, Any],
        etag: str | None = None,
        original: ContentFiltersResource | None = None,
    ) -> None:
        if isinstance(item_id, str):
            item_id = ObjectId(item_id)
        if original is None:
            original = await self.find_by_id(ObjectId(item_id))

            if original is None:
                raise SuperdeskApiError.notFoundError()

        updated = original.clone_with(updates)
        await self._validate_no_circular_reference(updated, item_id)
        await super().update(item_id, updates, etag, original)

    async def on_delete(self, doc: ContentFiltersResource) -> None:
        # check if the filter is referenced by any subscribers...
        subscribers = await self._get_referencing_subscribers(doc.id)
        if len(subscribers) > 0:
            references = ",".join(subscriber.name for subscriber in subscribers)
            raise SuperdeskApiError.badRequestError(
                gettext("Content filter has been referenced by subscriber(s) {references}").format(
                    references=references
                )
            )

        # check if the filter is referenced by any routing schemes...
        schemes = self._get_referencing_routing_schemes(doc.id)
        if len(schemes) > 0:
            references = ",".join(s["name"] for s in schemes)
            raise SuperdeskApiError.badRequestError(
                gettext("Content filter has been referenced by routing scheme(s) {references}").format(
                    references=references
                )
            )

        # check if the filter is referenced by any other content filters...
        referenced_filters = await _get_content_filters_by_content_filter(doc.id)
        if len(referenced_filters) > 0:
            references = ",".join([pf.name for pf in referenced_filters])
            raise SuperdeskApiError.badRequestError(
                gettext("Content filter has been referenced in {references})").format(references=references)
            )

        await super().on_delete(doc)

    async def _validate_no_circular_reference(
        self, content_filter: ContentFiltersResource, filter_id: ObjectId
    ) -> None:
        if not content_filter.content_filter:
            return

        for expression in content_filter.content_filter:
            if not expression.expression.pf:
                continue

            for current_filter_id in expression.expression.pf:
                if current_filter_id != filter_id:
                    raise SuperdeskApiError.badRequestError(
                        gettext("Circular dependency error in content filters:{filter}").format(
                            filter=content_filter.name
                        )
                    )
                current_filter = await self.find_by_id(current_filter_id)
                if current_filter:
                    await self._validate_no_circular_reference(current_filter, filter_id)

    async def _get_referencing_subscribers(self, filter_id: ObjectId) -> list[SubscribersResource]:
        """Fetch all subscribers that contain a reference to the given filter.

        :param str filter_id: the referenced filter's ID
        :return: DB cursor over the results
        :rtype: list[SubscribersResourceModel]
        """

        subscribers_service = SubscribersResource.get_service()
        subscribers: list[SubscribersResource] = []

        products = await ProductsResource.get_service().search({"content_filter.filter_id": filter_id})
        async for product in products:
            subscribers.extend(
                await subscribers_service.get_all_list(
                    {"$or": [{"products": product.id}, {"api_products": product.id}]}
                )
            )

        return subscribers

    def _get_referencing_routing_schemes(self, filter_id: ObjectId) -> list[dict]:
        """Fetch all routing schemes that contain a reference to the given filter.

        :param ObjectId filter_id: the referenced filter's ID
        :return: DB cursor over the results
        :rtype: :py:class:`pymongo.cursor.Cursor`
        """
        routing_schemes_service = get_resource_service("routing_schemes")
        return list(routing_schemes_service.get_from_mongo(req=None, lookup={"rules.filter": filter_id}))
