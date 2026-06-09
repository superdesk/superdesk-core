from typing import Any

from bson import ObjectId
from pymongo import UpdateOne

from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from superdesk.core.resources import AsyncResourceService
from superdesk.default_settings import DATE_FORMAT

from .models import ContentList, ContentListItem
from .webhooks import enqueue_webhook_deliveries


class ContentListsService(AsyncResourceService[ContentList]):
    async def on_update(self, updates: dict[str, Any], original: ContentList) -> None:
        updates.pop("content_list_items_updated_at", None)
        await super().on_update(updates, original)

    async def on_created(self, docs: list[ContentList]) -> None:
        await super().on_created(docs)
        # Let other open clients live-add the new list without a refresh.
        for doc in docs:
            push_notification("content_list:created", _id=str(doc.id))

    async def on_updated(self, updates: dict[str, Any], original: ContentList) -> None:
        await super().on_updated(updates, original)
        # List metadata changed (name, limit, ...) — let open clients refresh it.
        push_notification("content_list:updated", _id=str(original.id))

    async def on_deleted(self, doc: ContentList) -> None:
        await ContentListItemsService().delete_many({"list_id": doc.id})
        await super().on_deleted(doc)
        push_notification("content_list:deleted", _id=str(doc.id))


class ContentListItemsService(AsyncResourceService[ContentListItem]):
    async def bulk_patch(self, list_id: ObjectId, data: dict) -> ContentList:
        """Process a batch of add/move/delete actions on a content list's items.

        Uses ``updatedAt`` in the payload for optimistic concurrency control instead of
        the standard etag header. Updates ``content_list_items_updated_at`` directly via
        MongoDB to bypass the ``on_update`` hook, which strips that field from all updates.
        """
        if not data:
            raise SuperdeskApiError.badRequestError("Request body is required")
        if "items" not in data:
            raise SuperdeskApiError.badRequestError("items field is required")
        if "updatedAt" not in data:
            raise SuperdeskApiError.badRequestError("updatedAt field is required")

        lists_service = ContentListsService()
        content_list = await lists_service.find_by_id(list_id)
        if content_list is None:
            raise SuperdeskApiError.notFoundError(f"Content list {list_id} not found")

        list_items_updated_at = content_list.content_list_items_updated_at
        if list_items_updated_at and list_items_updated_at.strftime(DATE_FORMAT) != data["updatedAt"]:
            raise SuperdeskApiError.conflictError("Content list items have been modified")

        touched_contents: list[str] = []
        for item_data in data["items"]:
            action = item_data.get("action")
            content_id = str(item_data["contentId"])

            if action == "add":
                await self.create(
                    [
                        {
                            "list_id": list_id,
                            "content": content_id,
                            "position": item_data.get("position"),
                            "sticky": item_data.get("sticky", False),
                            "sticky_position": item_data.get("stickyPosition"),
                            "enabled": True,
                        }
                    ]
                )
                touched_contents.append(content_id)
            elif action == "move":
                existing = await self.find_one(req=None, list_id=list_id, content=content_id)
                if existing:
                    new_sticky = item_data.get("sticky", existing.sticky)
                    await self.update(existing.id, {"position": item_data.get("position"), "sticky": new_sticky})
                    touched_contents.append(content_id)
            elif action == "delete":
                existing = await self.find_one(req=None, list_id=list_id, content=content_id)
                if existing:
                    await self.delete(existing)

        await self._renumber(list_id, touched_contents)

        await lists_service.mongo_async.update_one(
            {"_id": list_id},
            {"$set": {"content_list_items_updated_at": utcnow()}},
        )
        result = await lists_service.find_by_id(list_id)
        assert result is not None

        # Tell every open client (including the editor's other tabs) that this
        # list's items changed, so they can live-refresh instead of waiting for
        # a manual page reload.
        push_notification("content_list:items_updated", list_id=str(list_id))

        # Notify external subscribers (webhooks) of the item change out of band.
        await enqueue_webhook_deliveries("content_list:items_updated", list_id)

        return result

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
            rank = touched_rank.get(d.get("content"))
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
