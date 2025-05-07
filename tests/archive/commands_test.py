from unittest.mock import patch
from datetime import datetime

from bson import ObjectId

from superdesk.tests import TestCase, utils as test_utils
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent


class RemoveExpiredContentTestCase(TestCase):
    async def test_is_expired(self):
        command = RemoveExpiredContent()
        item = {"expiry": None, "_id": "foo"}
        now = utcnow()
        self.assertFalse(await command._can_remove_item(item, now))

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

        archived_items = await test_utils.find_many("archived")
        assert 0 == len(archived_items)
