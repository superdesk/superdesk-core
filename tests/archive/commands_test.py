from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent
from datetime import datetime, timedelta
from unittest.mock import patch
from bson import ObjectId


class RemoveExpiredContentTestCase(TestCase):
    test_context = False

    def test_is_expired(self):
        now = utcnow()
        command = RemoveExpiredContent()
        item = {"expiry": None, "_id": "foo", "state": "draft", "_updated": now}
        self.assertFalse(command._can_remove_item(item, now))
        item["_updated"] = now - timedelta(days=30)
        self.assertTrue(command._can_remove_item(item, now))
        item["expiry"] = now + timedelta(days=1)
        self.assertFalse(command._can_remove_item(item, now))

    def test_spiked_expired_without_explicit_expiry(self):
        now = utcnow()

        self.app.data.insert(
            "archive",
            [
                {"type": "text", "state": "spiked", "_updated": now - timedelta(days=50)},
                {
                    "type": "text",
                    "state": "in_progress",
                    "_updated": now - timedelta(days=50),
                    "task": {"desk": "sports"},
                    "expiry": None,
                },
            ],
        )

        assert self.app.data.find_all("archive").count() == 2

        RemoveExpiredContent().run()

        assert self.app.data.find_all("archive").count() == 0

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
