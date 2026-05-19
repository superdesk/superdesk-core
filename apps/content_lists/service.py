from typing import Any

from bson import ObjectId

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

        for item_data in data["items"]:
            action = item_data.get("action")
            content_id = str(item_data["contentId"])

            if action == "add":
                new_position = item_data.get("position")
                if new_position is not None:
                    await self._shift_positions_up(list_id, new_position)
                await self.create(
                    [
                        {
                            "list_id": list_id,
                            "content": content_id,
                            "position": new_position,
                            "sticky": item_data.get("sticky", False),
                            "sticky_position": item_data.get("stickyPosition"),
                            "enabled": True,
                        }
                    ]
                )
            elif action == "move":
                existing = await self.find_one(req=None, list_id=list_id, content=content_id)
                if existing:
                    new_position = item_data.get("position")
                    await self._shift_positions_for_move(list_id, existing.id, existing.position, new_position)
                    await self.update(existing.id, {"position": new_position})
            elif action == "delete":
                existing = await self.find_one(req=None, list_id=list_id, content=content_id)
                if existing:
                    old_position = existing.position
                    await self.delete(existing)
                    if old_position is not None:
                        await self._shift_positions_down(list_id, old_position)

        await lists_service.mongo_async.update_one(
            {"_id": list_id},
            {"$set": {"content_list_items_updated_at": utcnow()}},
        )
        result = await lists_service.find_by_id(list_id)
        assert result is not None
        return result

    async def _shift_positions_up(self, list_id: ObjectId, position: int) -> None:
        """Make room at ``position`` by incrementing the position of every item at or after it."""
        await self.mongo_async.update_many(
            {"list_id": list_id, "sticky": {"$ne": True}, "position": {"$gte": position}},
            {"$inc": {"position": 1}},
        )

    async def _shift_positions_down(self, list_id: ObjectId, position: int) -> None:
        """Close the gap at ``position`` by decrementing the position of every item after it."""
        await self.mongo_async.update_many(
            {"list_id": list_id, "sticky": {"$ne": True}, "position": {"$gt": position}},
            {"$inc": {"position": -1}},
        )

    async def _shift_positions_for_move(
        self,
        list_id: ObjectId,
        item_id: ObjectId,
        old_position: int | None,
        new_position: int | None,
    ) -> None:
        """Reorder items affected by moving a single item from ``old_position`` to ``new_position``."""
        if new_position == old_position:
            return
        if old_position is None and new_position is not None:
            await self._shift_positions_up(list_id, new_position)
            return
        if new_position is None and old_position is not None:
            await self._shift_positions_down(list_id, old_position)
            return
        assert old_position is not None and new_position is not None
        if new_position < old_position:
            await self.mongo_async.update_many(
                {
                    "list_id": list_id,
                    "sticky": {"$ne": True},
                    "_id": {"$ne": item_id},
                    "position": {"$gte": new_position, "$lt": old_position},
                },
                {"$inc": {"position": 1}},
            )
        else:
            await self.mongo_async.update_many(
                {
                    "list_id": list_id,
                    "sticky": {"$ne": True},
                    "_id": {"$ne": item_id},
                    "position": {"$gt": old_position, "$lte": new_position},
                },
                {"$inc": {"position": -1}},
            )
