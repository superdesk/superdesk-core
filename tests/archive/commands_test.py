from unittest.mock import patch
from datetime import datetime, timedelta

from bson import ObjectId

from superdesk.tests import TestCase, utils as test_utils
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent


class RemoveExpiredContentTestCase(TestCase):
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
        await test_utils.post_items(
            "archived",
            [
                {
                    "type": "picture",
                    "_id": ObjectId.from_datetime(datetime(2024, 1, 1)),
                    "item_id": "test",
                    "guid": "test",
                },
            ],
        )

        with patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1}):
            await RemoveExpiredContent().run()

        assert await test_utils.count("archived") == 0
