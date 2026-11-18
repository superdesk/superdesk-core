from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from datetime import datetime, timedelta
from unittest.mock import patch
from bson import ObjectId
from celery.exceptions import SoftTimeLimitExceeded


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

    def test_archived_expiry_preserves_production_item_and_media(self):
        protected_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        expired_id = ObjectId.from_datetime(datetime(2024, 1, 2))
        self.app.data.insert("archive", [{"_id": "protected", "type": "picture"}])

        for legal_archive in (True, False):
            with self.subTest(legal_archive=legal_archive):
                settings = {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": legal_archive}
                self.app.data.insert(
                    "archived",
                    [
                        {"_id": protected_id, "item_id": "protected", "guid": "protected", "type": "picture"},
                        {"_id": expired_id, "item_id": "expired", "guid": "expired", "type": "picture"},
                    ],
                )
                with patch.dict(self.app.config, settings):
                    with (
                        patch("apps.archive.commands.signals.archived_item_removed.send") as removed_signal,
                        patch("apps.archive.commands.remove_media_files") as remove_media,
                    ):
                        RemoveExpiredContent()._remove_expired_archived_items(utcnow())

                assert self.app.data.find_all("archived").count() == 0
                assert self.app.data.find_one("archive", None, _id="protected") is not None
                assert {call.kwargs["item"]["_id"] for call in removed_signal.call_args_list} == {
                    protected_id,
                    expired_id,
                }
                if legal_archive:
                    remove_media.assert_not_called()
                else:
                    remove_media.assert_called_once()
                    assert remove_media.call_args.args[0]["item_id"] == "expired"

    def test_normal_archived_delete_still_validates_production_item(self):
        self.app.data.insert("archive", [{"_id": "protected", "type": "picture"}])
        item = {
            "_id": ObjectId.from_datetime(datetime(2024, 1, 1)),
            "item_id": "protected",
            "guid": "protected",
            "type": "picture",
        }
        self.app.data.insert("archived", [item])

        with self.assertRaises(SuperdeskApiError):
            get_resource_service("archived").delete_docs([item.copy()])

        assert self.app.data.find_all("archived").count() == 1

    def test_archived_cleanup_failure_does_not_block_remaining_items(self):
        first_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        second_id = ObjectId.from_datetime(datetime(2024, 1, 2))
        for failure in ("signal", "media"):
            with self.subTest(failure=failure):
                self.app.data.insert(
                    "archived",
                    [
                        {"_id": first_id, "item_id": "first", "guid": "first", "type": "picture"},
                        {"_id": second_id, "item_id": "second", "guid": "second", "type": "picture"},
                    ],
                )
                with (
                    patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": False}),
                    patch("apps.archive.commands.signals.archived_item_removed.send") as removed_signal,
                    patch("apps.archive.commands.remove_media_files") as remove_media,
                    self.assertLogs("apps.archive.commands", level="ERROR") as logs,
                ):
                    failing_mock = removed_signal if failure == "signal" else remove_media
                    failing_mock.side_effect = [RuntimeError("cleanup failed"), None]
                    RemoveExpiredContent()._remove_expired_archived_items(utcnow())

                assert self.app.data.find_all("archived").count() == 0
                assert removed_signal.call_count == 2
                assert remove_media.call_args.args[0]["item_id"] == "second"
                assert str(first_id) in logs.output[0]
                assert "item_id=first" in logs.output[0]

    def test_archived_cleanup_does_not_swallow_soft_time_limit(self):
        self.app.data.insert(
            "archived",
            [
                {
                    "_id": ObjectId.from_datetime(datetime(2024, 1, 1)),
                    "item_id": "expired",
                    "guid": "expired",
                    "type": "picture",
                },
            ],
        )
        with (
            patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1}),
            patch("apps.archive.commands.signals.archived_item_removed.send", side_effect=SoftTimeLimitExceeded),
            self.assertRaises(SoftTimeLimitExceeded),
        ):
            RemoveExpiredContent()._remove_expired_archived_items(utcnow())
