from typing import Any

from bson import ObjectId
from pymongo import UpdateOne

from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError
from superdesk.core.resources import AsyncResourceService
from superdesk.default_settings import DATE_FORMAT

from .models import ContentList, ContentListItem


class ContentListsService(AsyncResourceService[ContentList]):
    async def on_update(self, updates: dict[str, Any], original: ContentList) -> None:
        updates.pop("content_list_items_updated_at", None)
        await super().on_update(updates, original)

    async def on_deleted(self, doc: ContentList) -> None:
        await ContentListItemsService().delete_many({"list_id": doc.id})
        await super().on_deleted(doc)


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
        return result

    async def _renumber(self, list_id: ObjectId, touched_contents: list[str]) -> None:
        """Rewrite non-sticky positions as a contiguous ``0..N-1`` sequence.

        Items in ``touched_contents`` (added or moved in this batch) win position
        ties: when an item lands on a slot already occupied, the touched item
        keeps the slot and the prior occupant shifts to the next one. Later
        entries in ``touched_contents`` outrank earlier ones.
        """
        docs = await self.mongo_async.find(
            {"list_id": list_id, "sticky": {"$ne": True}},
            projection={"_id": 1, "content": 1, "position": 1},
        ).to_list(None)

        touched_rank = {c: i for i, c in enumerate(touched_contents)}

        def sort_key(d: dict) -> tuple:
            pos = d.get("position")
            rank = touched_rank.get(d.get("content"))
            return (
                pos is None,
                pos if pos is not None else 0,
                rank is None,
                -rank if rank is not None else 0,
                d["_id"],
            )

        docs.sort(key=sort_key)

        ops = [
            UpdateOne({"_id": doc["_id"]}, {"$set": {"position": i}})
            for i, doc in enumerate(docs)
            if doc.get("position") != i
        ]
        if ops:
            await self.mongo_async.bulk_write(ops, ordered=False)
