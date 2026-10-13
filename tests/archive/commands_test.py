import copy
from unittest.mock import patch
from datetime import datetime, timedelta

from bson import ObjectId

from superdesk.tests import TestCase, utils as test_utils
from superdesk.utc import utcnow
from superdesk import get_resource_service
from apps.archive.commands import RemoveExpiredContent


class RemoveExpiredContentTestCase(TestCase):
    async def test_expiry_extended_after_selection(self):
        now = utcnow()
        service = get_resource_service("archive")
        items = [
            {
                "_id": state,
                "guid": state,
                "type": "text",
                "state": state,
                "expiry": now - timedelta(days=1),
                "_updated": now - timedelta(days=2),
                "_current_version": 1,
                "unique_name": state,
            }
            for state in ("in_progress", "spiked", "killed", "recalled")
        ]
        await self.app.data.insert_async("archive", items)
        await self.app.data.insert_async(
            "archive_versions", [{"_id_document": item["_id"], "type": "text"} for item in items]
        )
        await self.app.data.insert_async(
            "published",
            [{"_id": item["_id"], "item_id": item["_id"], "type": "text"} for item in items],
        )

        async def selected_items(*args, **kwargs):
            for item in items:
                original = await service.find_one_async(req=None, _id=item["_id"])
                await service.system_update_async(
                    item["_id"], {"expiry": now + timedelta(days=1)}, original, check_etag=True
                )
            yield copy.deepcopy(items)
            yield []

        with patch.object(service, "get_expired_items", side_effect=selected_items):
            await RemoveExpiredContent()._remove_expired_items(now)

        assert await test_utils.count("archive") == len(items)
        assert await test_utils.count("archive_versions") == len(items)
        assert await test_utils.count("published") == len(items)
        for item in items:
            elastic_item = self.app.data.elastic.find_one("archive", req=None, _id=item["_id"])
            assert elastic_item["expiry"] == now + timedelta(days=1)

    async def test_is_expired(self):
        now = utcnow()
        command = RemoveExpiredContent()
        item = {"expiry": None, "_id": "foo", "state": "draft", "_updated": now}
        self.assertFalse(await command._can_remove_item(item, now))
        item["_updated"] = now - timedelta(days=30)
        self.assertTrue(await command._can_remove_item(item, now))
        item["expiry"] = now + timedelta(days=1)
        self.assertFalse(await command._can_remove_item(item, now))

    async def test_spiked_expired_without_explicit_expiry(self):
        now = utcnow()

        desk_id = (await test_utils.post_items("desks", [{"name": "sports"}]))[0]

        await self.app.data.insert_async(
            "archive",
            [
                {"type": "text", "state": "spiked", "_updated": now - timedelta(days=50)},
                {
                    "type": "text",
                    "state": "in_progress",
                    "_updated": now - timedelta(days=50),
                    "task": {"desk": desk_id},
                    "expiry": None,
                },
            ],
        )

        assert await test_utils.count("archive") == 2

        await RemoveExpiredContent().run()

        assert await test_utils.count("archive") == 0

    async def test_expired_archived_picture(self):
        expired_item_id = "test"
        await test_utils.post_items(
            "archived",
            [
                {
                    "type": "picture",
                    "_id": ObjectId.from_datetime(datetime(2024, 1, 1)),
                    "item_id": expired_item_id,
                    "guid": expired_item_id,
                },
            ],
        )
        await test_utils.post_items(
            "archive",
            [{"_id": expired_item_id, "type": "text", "state": "published"}],
        )

        with patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1}):
            await RemoveExpiredContent().run()

        assert await test_utils.count("archived") == 0
