from typing import Any

from bson import ObjectId
from pydantic import ValidationError
from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from superdesk.core.resources import AsyncResourceService
from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error
from superdesk.default_settings import DATE_FORMAT

from .models import (
    ContentList,
    ContentListItem,
    ContentListBulkActions,
    ContentListBulkActionItem,
    ContentListItemAction,
)
from .webhooks import enqueue_webhook_deliveries

ITEMS_UPDATED_EVENT = "content_list:items_updated"
LIST_CREATED_EVENT = "content_list:created"
LIST_UPDATED_EVENT = "content_list:updated"
LIST_DELETED_EVENT = "content_list:deleted"

DUPLICATE_ITEMS_ERROR = "Content list cannot be saved because it contains duplicated items"


class ContentListsService(AsyncResourceService[ContentList]):
    async def on_update(self, updates: dict[str, Any], original: ContentList) -> None:
        updates.pop("content_list_items_updated_at", None)
        await super().on_update(updates, original)

    async def on_created(self, docs: list[ContentList]) -> None:
        await super().on_created(docs)
        for doc in docs:
            push_notification(LIST_CREATED_EVENT, _id=str(doc.id), extension="content-lists")
            await enqueue_webhook_deliveries(LIST_CREATED_EVENT, doc.id)

    async def on_updated(self, updates: dict[str, Any], original: ContentList) -> None:
        await super().on_updated(updates, original)
        push_notification(LIST_UPDATED_EVENT, _id=str(original.id), extension="content-lists")
        await enqueue_webhook_deliveries(LIST_UPDATED_EVENT, original.id)

    async def on_deleted(self, doc: ContentList) -> None:
        await ContentListItemsService().delete_many({"list_id": doc.id})
        await super().on_deleted(doc)
        push_notification(LIST_DELETED_EVENT, _id=str(doc.id), extension="content-lists")
        await enqueue_webhook_deliveries(LIST_DELETED_EVENT, doc.id)


class ContentListItemsService(AsyncResourceService[ContentListItem]):
    async def bulk_patch(self, list_id: ObjectId, data: dict) -> ContentList:
        """Process a batch of add/move/delete actions on a content list's items.

        Uses ``updatedAt`` in the payload for optimistic concurrency control instead of
        the standard etag header. Updates ``content_list_items_updated_at`` directly via
        MongoDB to bypass the ``on_update`` hook, which strips that field from all updates.
        """
        try:
            actions = ContentListBulkActions.from_dict(data or {})
        except ValidationError as validation_error:
            raise SuperdeskApiError.badRequestError(
                payload=get_field_errors_from_pydantic_validation_error(validation_error)
            )

        lists_service = ContentListsService()
        content_list = await lists_service.find_by_id(list_id)
        if content_list is None:
            raise SuperdeskApiError.notFoundError(f"Content list {list_id} not found")

        list_items_updated_at = content_list.content_list_items_updated_at
        if list_items_updated_at and list_items_updated_at.strftime(DATE_FORMAT) != actions.updated_at:
            raise SuperdeskApiError.conflictError("Content list items have been modified")

        items = self._cancel_pending_add_deletes(actions.items)
        await self._validate_no_duplicates(list_id, items)

        touched_contents: list[str] = []
        for item in items:
            if item.action == ContentListItemAction.ADD:
                try:
                    await self.create(
                        [
                            {
                                "list_id": list_id,
                                "content": item.content_id,
                                "position": item.position,
                                "sticky": item.sticky or False,
                                "sticky_position": item.sticky_position,
                                "enabled": True,
                            }
                        ]
                    )
                except DuplicateKeyError:
                    # Concurrent request added the same content between the
                    # upfront validation and this insert.
                    raise SuperdeskApiError.badRequestError(DUPLICATE_ITEMS_ERROR)
                touched_contents.append(item.content_id)
            elif item.action == ContentListItemAction.MOVE:
                existing = await self.find_one(req=None, list_id=list_id, content=item.content_id)
                if existing:
                    new_sticky = item.sticky if item.sticky is not None else existing.sticky
                    await self.update(existing.id, {"position": item.position, "sticky": new_sticky})
                    touched_contents.append(item.content_id)
            elif item.action == ContentListItemAction.DELETE:
                existing = await self.find_one(req=None, list_id=list_id, content=item.content_id)
                if existing:
                    await self.delete(existing)

        await self._renumber(list_id, touched_contents)

        await lists_service.mongo_async.update_one(
            {"_id": list_id},
            {"$set": {"content_list_items_updated_at": utcnow()}},
        )
        result = await lists_service.find_by_id(list_id)
        assert result is not None

        push_notification(ITEMS_UPDATED_EVENT, list_id=str(list_id), extension="content-lists")
        await enqueue_webhook_deliveries(ITEMS_UPDATED_EVENT, list_id)

        return result

    @staticmethod
    def _cancel_pending_add_deletes(items: list[ContentListBulkActionItem]) -> list[ContentListBulkActionItem]:
        """Drop add/delete pairs for the same content that cancel out.

        Clients keep unsaved actions queued: adding an article and then
        removing it again before saving arrives as an ``add`` followed by a
        ``delete`` for the same content. The added row never existed on the
        server, so the pair is a no-op — applying the add literally would
        duplicate an existing item. The reverse order (``delete`` followed by
        ``add``, re-adding existing content at a new position) is left intact.
        """
        result: list[ContentListBulkActionItem] = []
        for item in items:
            if item.action == ContentListItemAction.DELETE:
                for index in range(len(result) - 1, -1, -1):
                    if (
                        result[index].action == ContentListItemAction.ADD
                        and result[index].content_id == item.content_id
                    ):
                        del result[index]
                        break
                else:
                    result.append(item)
            else:
                result.append(item)
        return result

    async def _validate_no_duplicates(self, list_id: ObjectId, items: list[ContentListBulkActionItem]) -> None:
        """Reject the whole batch upfront when an add would duplicate an item.

        Replays the batch actions against the list's current contents, so a
        duplicate is caught before any change is applied — the batch stays
        retryable once the client drops the duplicate — while deleting and
        re-adding the same content within one batch remains valid.
        """
        docs = await self.mongo_async.find({"list_id": list_id}, projection={"content": 1}).to_list(None)
        contents = {doc["content"] for doc in docs}
        for item in items:
            if item.action == ContentListItemAction.ADD:
                if item.content_id in contents:
                    raise SuperdeskApiError.badRequestError(DUPLICATE_ITEMS_ERROR)
                contents.add(item.content_id)
            elif item.action == ContentListItemAction.DELETE:
                contents.discard(item.content_id)

    async def _renumber(self, list_id: ObjectId, touched_contents: list[str]) -> None:
        """Reassign positions so every item has a unique slot.

        Sticky items keep their declared position. Non-sticky items in
        ``touched_contents`` (added or moved in this batch) also anchor at the
        position they were just set to. Remaining untouched non-sticky items
        fill the lowest-numbered free positions in their previous order. If
        two anchors land on the same slot, sticky beats non-sticky and the
        most recently touched wins within a group; the loser spills to the
        nearest higher free slot.
        """
        docs = await self.mongo_async.find(
            {"list_id": list_id},
            projection={"_id": 1, "content": 1, "position": 1, "sticky": 1},
        ).to_list(None)
        if not docs:
            return

        touched_rank = {c: i for i, c in enumerate(touched_contents)}

        def anchor_priority(d: dict) -> tuple:
            content = d.get("content")
            rank = touched_rank.get(content) if content is not None else None
            return (
                0 if d.get("sticky") else 1,
                -(rank if rank is not None else -1),
                d["_id"],
            )

        anchors = [d for d in docs if d.get("sticky") or d.get("content") in touched_rank]
        anchors.sort(key=anchor_priority)

        placement: dict[int, dict] = {}
        for doc in anchors:
            pos = doc.get("position")
            slot = pos if pos is not None and pos >= 0 else 0
            while slot in placement:
                slot += 1
            placement[slot] = doc

        rest = [d for d in docs if not d.get("sticky") and d.get("content") not in touched_rank]
        rest.sort(
            key=lambda d: (
                d.get("position") is None,
                d.get("position") if d.get("position") is not None else 0,
                d["_id"],
            )
        )
        next_slot = 0
        for doc in rest:
            while next_slot in placement:
                next_slot += 1
            placement[next_slot] = doc
            next_slot += 1

        ops = [
            UpdateOne({"_id": doc["_id"]}, {"$set": {"position": i}})
            for i, doc in placement.items()
            if doc.get("position") != i
        ]
        if ops:
            await self.mongo_async.bulk_write(ops, ordered=False)
