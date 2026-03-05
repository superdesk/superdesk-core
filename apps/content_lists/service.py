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
    async def bulk_update(self, list_id: ObjectId, data: dict) -> ContentList:
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
            elif action == "move":
                existing = await self.find_one(req=None, list_id=list_id, content=content_id)
                if existing:
                    await self.update(existing.id, {"position": item_data.get("position")})
            elif action == "delete":
                existing = await self.find_one(req=None, list_id=list_id, content=content_id)
                if existing:
                    await self.delete(existing)

        await lists_service.mongo_async.update_one(
            {"_id": list_id},
            {"$set": {"content_list_items_updated_at": utcnow()}},
        )
        return await lists_service.find_by_id(list_id)
