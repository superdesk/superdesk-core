from typing import Any

from quart_babel import gettext

from superdesk.core import get_current_app
from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError

from superdesk.types import PublishQueueResource, SubscribersResource, PublishQueueState
from superdesk.publish_async.subscribers.utils import generate_sequence_number
from superdesk.notification import push_notification


class PublishQueueService(AsyncResourceService[PublishQueueResource]):
    async def on_create(self, docs: list[PublishQueueResource]) -> None:
        await super().on_create(docs)
        subscriber_service = SubscribersResource.get_service()

        for doc in docs:
            doc.state = (
                PublishQueueState.SUCCESS
                if doc.destination and doc.destination.delivery_type == "content_api"
                else doc.state or PublishQueueState.PENDING
            )
            doc.moved_to_legal = False

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
