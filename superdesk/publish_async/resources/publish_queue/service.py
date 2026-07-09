import logging
from typing import Any, Sequence

from quart_babel import gettext
from pymongo.errors import DuplicateKeyError

from superdesk.core import get_current_app
from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError

from superdesk.types import PublishQueueResource, SubscribersResource, PublishQueueState
from superdesk.publish_async.utils import generate_sequence_number
from superdesk.notification import push_notification


logger = logging.getLogger(__name__)


class PublishQueueService(AsyncResourceService[PublishQueueResource]):
    def _get_destination_identity(self, doc: PublishQueueResource) -> tuple[str, str]:
        if not doc.destination:
            return "none", "none"

        destination_id = str(doc.destination._id) if doc.destination._id else None
        if destination_id:
            return "id", destination_id

        if doc.destination.delivery_type == "content_api":
            return "content_api", "content_api"

        return (
            str(doc.destination.delivery_type or "none"),
            str(doc.destination.name or "none"),
        )

    def _get_duplicate_lookup(self, doc: PublishQueueResource) -> dict[str, Any]:
        lookup: dict[str, Any] = {
            "item_id": doc.item_id,
            "item_version": doc.item_version,
            "subscriber_id": doc.subscriber_id,
            "publishing_action": doc.publishing_action,
        }

        if doc.destination and doc.destination._id:
            lookup["destination._id"] = doc.destination._id
        elif doc.destination and doc.destination.delivery_type == "content_api":
            lookup["destination.delivery_type"] = "content_api"
        elif doc.destination:
            lookup["destination.delivery_type"] = doc.destination.delivery_type
            lookup["destination.name"] = doc.destination.name

        return lookup

    async def create(self, docs: Sequence[PublishQueueResource | dict[str, Any]]) -> list[PublishQueueResource]:
        instances = await self._convert_dicts_to_model(docs)
        created_instances: list[PublishQueueResource] = []
        identity_to_instance: dict[tuple[Any, ...], PublishQueueResource] = {}
        seen_identities: set[tuple[Any, ...]] = set()

        for doc in instances:
            destination_identity_type, destination_identity_value = self._get_destination_identity(doc)
            identity = (
                doc.item_id,
                doc.item_version,
                doc.subscriber_id,
                doc.publishing_action,
                destination_identity_type,
                destination_identity_value,
            )

            if identity in seen_identities:
                existing_in_batch = identity_to_instance.get(identity)
                if existing_in_batch:
                    created_instances.append(existing_in_batch)
                logger.warning(
                    "Skipping duplicate publish queue item in request batch",
                    extra=dict(
                        item_id=doc.item_id,
                        item_version=doc.item_version,
                        subscriber_id=str(doc.subscriber_id),
                        publishing_action=doc.publishing_action,
                        destination_id=doc.destination._id if doc.destination else None,
                        destination_name=doc.destination.name if doc.destination else None,
                    ),
                )
                continue

            existing = await self.find_one(**self._get_duplicate_lookup(doc))
            if existing:
                created_instances.append(existing)
                identity_to_instance[identity] = existing
                logger.warning(
                    "Skipping duplicate publish queue item already in queue",
                    extra=dict(
                        item_id=doc.item_id,
                        item_version=doc.item_version,
                        subscriber_id=str(doc.subscriber_id),
                        publishing_action=doc.publishing_action,
                        destination_id=doc.destination._id if doc.destination else None,
                        destination_name=doc.destination.name if doc.destination else None,
                        existing_queue_id=str(existing.id),
                    ),
                )
                seen_identities.add(identity)
                continue

            seen_identities.add(identity)

            try:
                inserted = await super().create([doc])
                created_instances.extend(inserted)
                if inserted:
                    identity_to_instance[identity] = inserted[0]
            except DuplicateKeyError:
                existing = await self.find_one(**self._get_duplicate_lookup(doc))
                if existing:
                    created_instances.append(existing)
                    identity_to_instance[identity] = existing
                logger.warning(
                    "Skipping duplicate publish queue item",
                    extra=dict(
                        item_id=doc.item_id,
                        item_version=doc.item_version,
                        subscriber_id=str(doc.subscriber_id),
                        publishing_action=doc.publishing_action,
                        destination_id=doc.destination._id if doc.destination else None,
                        destination_name=doc.destination.name if doc.destination else None,
                    ),
                )
                continue

        return created_instances

    async def on_create(self, docs: list[PublishQueueResource]) -> None:
        await super().on_create(docs)
        subscriber_service = SubscribersResource.get_service()

        for doc in docs:
            doc.state = (
                PublishQueueState.SUCCESS
                if doc.destination and doc.destination.delivery_type == "content_api"
                else doc.state or PublishQueueState.PENDING
            )

            if not doc.published_seq_num:
                subscriber = await subscriber_service.find_by_id(doc.subscriber_id)
                if not subscriber:
                    raise SuperdeskApiError.badRequestError(
                        gettext(f"PublishQueue Subscriber {doc.subscriber_id} not found")
                    )
                doc.published_seq_num = await generate_sequence_number(subscriber)

    async def on_updated(self, updates: dict[str, Any], original: PublishQueueResource) -> None:
        await super().on_updated(updates, original)
        if updates.get("state", "") == original.state:
            return

        delivery_type: str | None = None

        try:
            delivery_type = updates["destination"]["delivery_type"]
        except (KeyError, TypeError):
            if original.destination:
                delivery_type = original.destination.delivery_type

        new_state = (
            PublishQueueState.SUCCESS
            if delivery_type == "content_api"
            else updates.get("state") or PublishQueueState.PENDING
        )

        push_notification(
            "publish_queue:update",
            queue_id=str(original.id),
            completed_at=updates["completed_at"].isoformat() if updates.get("completed_at") else None,
            state=new_state,
            error_message=updates.get("error_message"),
        )

    async def on_delete(self, doc: PublishQueueResource) -> None:
        # as encoded item is added manually to storage
        # we also need to remove it manually on delete
        if doc.encoded_item_id:
            get_current_app().storage.delete(doc.encoded_item_id)
        await super().on_delete(doc)

    async def delete_by_article_id(self, item_id: str) -> None:
        await self.delete_many({"item_id": item_id})
