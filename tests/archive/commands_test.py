from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent
from datetime import datetime
from unittest.mock import patch
from bson import ObjectId


class RemoveExpiredContentTestCase(TestCase):
    test_context = False

    def test_is_expired(self):
        command = RemoveExpiredContent()
        item = {"expiry": None, "_id": "foo"}
        now = utcnow()
        self.assertFalse(command._can_remove_item(item, now))

    def test_expired_archived_picture(self):
        self.app.data.insert(
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
            RemoveExpiredContent().run()

        archived_items = self.app.data.find_all("archived")
        assert 0 == archived_items.count()
