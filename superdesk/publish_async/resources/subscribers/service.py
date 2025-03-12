from typing import Any

from superdesk.core import get_config
from superdesk.core.resources import AsyncResourceService

from superdesk.types import (
    SubscribersResource,
    SubscriberSequenceSettings,
    ProductTypes,
    SequencesResource,
    ProductsResource,
)
from superdesk.errors import SuperdeskApiError
from superdesk.resource_fields import ID_FIELD
from superdesk.notification import push_notification

from .utils import get_subscriber_destination_id


class SubscribersService(AsyncResourceService[SubscribersResource]):
    async def on_create(self, docs: list[SubscribersResource]) -> None:
        await super().on_create(docs)
        for doc in docs:
            self._validate_seq_num_settings(doc)
            await self._validate_products_destinations(doc)
            for destination in doc.destinations or []:
                destination._id = get_subscriber_destination_id(destination)

    async def on_created(self, docs: list[SubscribersResource]) -> None:
        await super().on_created(docs)
        push_notification("subscriber:create", _id=[doc.id for doc in docs])

    async def on_update(self, updates: dict[str, Any], original: SubscribersResource) -> None:
        await super().on_update(updates, original)
        subscriber = original.clone_with(updates)
        self._validate_seq_num_settings(subscriber)
        updates["sequence_num_settings"] = (
            subscriber.sequence_num_settings.to_dict() if subscriber.sequence_num_settings else None
        )

        await self._validate_products_destinations(subscriber)
        self.keep_destinations_secrets(updates, original)

    async def on_updated(self, updates: dict[str, Any], original: SubscribersResource) -> None:
        await super().on_updated(updates, original)
        push_notification("subscriber:update", _id=[original.id])

    async def on_deleted(self, doc: SubscribersResource) -> None:
        await super().on_deleted(doc)
        await SequencesResource.get_service().delete_many({"key": f"ingest_providers_{doc.id}"})

    def keep_destinations_secrets(self, updates: dict[str, Any], original: SubscribersResource) -> None:
        """Populate the secrets removed on fetch so those won't be overriden on save."""
        original_destinations = original.destinations or []
        updates_destinations = updates.get("destinations") or []
        for destination in original_destinations:
            if not destination.config:
                continue
            dest_id = get_subscriber_destination_id(destination)
            for update_destination in updates_destinations:
                if dest_id == update_destination.get("_id"):
                    for field, value in destination.config.items():
                        update_destination["config"].setdefault(field, value)

    def _validate_seq_num_settings(self, subscriber: SubscribersResource) -> None:
        """
        Validates the 'sequence_num_settings' property if present in subscriber.

        Below are the validation rules:
            1.  If min value is present then it should be greater than 0
            2.  If min is present and max value isn't available then it's defaulted to MAX_VALUE_OF_PUBLISH_SEQUENCE

        :return: True if validation succeeds otherwise return False.
        """

        if not subscriber.sequence_num_settings:
            return

        min = 1 if subscriber.sequence_num_settings.min is None else subscriber.sequence_num_settings.min
        max = (
            get_config(int, "MAX_VALUE_OF_PUBLISH_SEQUENCE")
            if subscriber.sequence_num_settings.max is None
            else subscriber.sequence_num_settings.max
        )

        if min <= 0:
            raise SuperdeskApiError.badRequestError(
                payload={"sequence_num_settings.min": 1},
                message="Value of Minimum in Sequence Number Settings should " "be greater than 0",
            )

        if min >= max:
            raise SuperdeskApiError.badRequestError(
                payload={"sequence_num_settings.min": 1},
                message="Value of Minimum in Sequence Number Settings should " "be less than the value of Maximum",
            )

        subscriber.sequence_num_settings = SubscriberSequenceSettings(min=min, max=max)

    async def _validate_products_destinations(self, subscriber: SubscribersResource) -> None:
        """Validates the subscribers
            1. At least one destination or one api_products is specified.
            2. If direct products are specified then at least one destination is specified.
        :param dict subscriber:
        :return:
        """
        if not subscriber.is_active:
            return

        if not subscriber.destinations and not subscriber.api_products:
            raise SuperdeskApiError.badRequestError(
                payload={"destinations": {"required": 1}, "api_products": {"required": 1}},
                message="At least one destination or one API Product should " "be specified",
            )

        if len(subscriber.products or []) and not subscriber.destinations:
            raise SuperdeskApiError.badRequestError(
                payload={"destinations": {"required": 1}}, message="Destinations not specified."
            )

        if subscriber.products:
            lookup = {ID_FIELD: {"$in": subscriber.products}, "product_type": ProductTypes.API.value}
            products = await ProductsResource.get_names(lookup)
            if products:
                raise SuperdeskApiError.badRequestError(
                    payload={"products": 1}, message="Invalid Product Type. " "Products {}.".format(", ".join(products))
                )
        if subscriber.api_products:
            lookup = {
                ID_FIELD: {"$in": subscriber.api_products},
                "product_type": ProductTypes.DIRECT.value,
            }
            products = await ProductsResource.get_names(lookup)
            if products:
                raise SuperdeskApiError.badRequestError(
                    payload={"products": 1},
                    message="Invalid Product Type. " "API Products {}.".format(", ".join(products)),
                )
