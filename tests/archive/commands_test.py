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

    def test_production_delete_cleans_media_retained_after_archived_expiry(self):
        self._assert_retained_media_cleanup(keep_newer_snapshot=False)

    def test_final_archived_expiry_cleans_media_retained_from_older_snapshot(self):
        self._assert_retained_media_cleanup(keep_newer_snapshot=True)

    def test_production_delete_preserves_media_used_by_unpublished_duplicate(self):
        item_id = "expired-original"
        duplicate_id = "surviving-duplicate"
        media_id = "shared-media"
        archived_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        self.app.data.insert(
            "archive",
            [
                {
                    "_id": item_id,
                    "guid": item_id,
                    "type": "picture",
                    "state": "spiked",
                    "renditions": {"original": {"media": media_id}},
                },
                {
                    "_id": duplicate_id,
                    "guid": duplicate_id,
                    "type": "picture",
                    "state": "draft",
                    "renditions": {"original": {"media": media_id}},
                },
            ],
        )
        self.app.data.insert(
            "archived",
            [
                {
                    "_id": archived_id,
                    "item_id": item_id,
                    "guid": item_id,
                    "type": "picture",
                    "renditions": {"original": {"media": media_id}},
                },
            ],
        )
        self.app.data.insert(
            "media_references",
            [
                {"item_id": item_id, "media_id": media_id, "published": True},
                {"item_id": duplicate_id, "media_id": media_id, "published": False},
            ],
        )
        references = get_resource_service("media_references")

        with (
            patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": False}),
            patch.object(self.app.media, "delete") as delete_media,
        ):
            RemoveExpiredContent()._remove_expired_archived_items(utcnow())

            assert self.app.data.find_one("archived", None, _id=archived_id) is None
            assert references.find_one(None, item_id=item_id, media_id=media_id, published=True) is not None

            get_resource_service("archive").delete_by_article_ids([item_id])

        assert self.app.data.find_one("archive", None, _id=duplicate_id) is not None
        assert references.find_one(None, item_id=duplicate_id, media_id=media_id, published=False) is not None
        delete_media.assert_not_called()

    def _assert_retained_media_cleanup(self, keep_newer_snapshot):
        item_id = "deferred-media"
        item_guid = "external-media-guid"
        archived_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        newer_id = ObjectId()
        self.app.data.insert(
            "archive",
            [
                {
                    "_id": item_id,
                    "guid": item_guid,
                    "type": "picture",
                    "state": "spiked",
                    "renditions": {
                        "original": {"media": "current-media"},
                        "thumbnail": {"media": "shared-media"},
                    },
                },
            ],
        )
        self.app.data.insert(
            "archived",
            [
                {
                    "_id": archived_id,
                    "item_id": item_id,
                    "guid": item_guid,
                    "type": "picture",
                    "renditions": {"original": {"media": "old-media"}},
                },
            ],
        )
        if keep_newer_snapshot:
            self.app.data.insert(
                "archived",
                [
                    {
                        "_id": newer_id,
                        "item_id": item_id,
                        "guid": item_guid,
                        "type": "picture",
                        "renditions": {"original": {"media": "current-media"}},
                    },
                ],
            )
        self.app.data.insert(
            "media_references",
            [
                {"item_id": item_id, "media_id": media_id, "published": True}
                for media_id in ("current-media", "old-media", "shared-media")
            ]
            + [{"item_id": "other-item", "media_id": "shared-media", "published": True}],
        )
        references = get_resource_service("media_references")
        with (
            patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": False}),
            patch.object(self.app.media, "delete") as delete_media,
        ):
            RemoveExpiredContent()._remove_expired_archived_items(utcnow())

            assert self.app.data.find_one("archived", None, _id=archived_id) is None
            assert references.get_from_mongo(None, {"item_id": item_id}).count() == 3
            delete_media.assert_not_called()

            get_resource_service("archive").delete_by_article_ids([item_id])

            if keep_newer_snapshot:
                assert self.app.data.find_one("archive", None, _id=item_id) is None
                assert self.app.data.find_one("archived", None, _id=newer_id) is not None
                assert references.get_from_mongo(None, {"item_id": item_id}).count() == 3
                delete_media.assert_not_called()

                RemoveExpiredContent()._remove_expired_archived_items(utcnow() + timedelta(minutes=2))

        assert self.app.data.find_one("archive", None, _id=item_id) is None
        assert self.app.data.find_one("archived", None, item_id=item_id) is None
        assert references.get_from_mongo(None, {"item_id": item_id}).count() == 0
        assert references.find_one(None, item_id="other-item", media_id="shared-media") is not None
        self.assertCountEqual(
            ["current-media", "old-media"],
            [call.args[0] for call in delete_media.call_args_list],
        )

    def test_archive_version_cleanup_uses_production_id_instead_of_version_id_or_guid(self):
        item_id = "version-production-id"
        version_id = ObjectId()
        self.app.data.insert(
            "archive_versions",
            [
                {
                    "_id": version_id,
                    "_id_document": item_id,
                    "guid": "external-media-guid",
                    "type": "picture",
                    "renditions": {
                        "original": {"media": "version-media"},
                        "thumbnail": {"media": "unpublished-media"},
                    },
                },
            ],
        )
        self.app.data.insert(
            "media_references",
            [
                {"item_id": item_id, "media_id": "version-media", "published": True},
                {"item_id": item_id, "media_id": "unpublished-media", "published": False},
            ],
        )
        with patch.dict(self.app.config, {"LEGAL_ARCHIVE": False}), patch.object(
            self.app.media, "delete"
        ) as delete_media:
            get_resource_service("archive_versions").delete_action({"_id": version_id})

        assert self.app.data.find_one("archive_versions", None, _id=version_id) is None
        assert list(get_resource_service("media_references").get_from_mongo(None, {"item_id": item_id})) == []
        self.assertCountEqual(
            ["version-media", "unpublished-media"],
            [call.args[0] for call in delete_media.call_args_list],
        )

    def test_production_delete_retains_media_needed_by_other_repositories(self):
        for repository in ("archived", "published", "legal_archive"):
            with self.subTest(repository=repository):
                item_id = "retained-" + repository
                self.app.data.insert(
                    "archive",
                    [
                        {
                            "_id": item_id,
                            "guid": item_id,
                            "type": "picture",
                            "state": "spiked",
                            "renditions": {"original": {"media": item_id}},
                        },
                    ],
                )
                if repository != "legal_archive":
                    self.app.data.insert(repository, [{"item_id": item_id, "guid": item_id, "type": "picture"}])
                self.app.data.insert(
                    "media_references",
                    [{"item_id": item_id, "media_id": item_id, "published": True}],
                )
                with (
                    patch.dict(self.app.config, {"LEGAL_ARCHIVE": repository == "legal_archive"}),
                    patch.object(self.app.media, "delete") as delete_media,
                ):
                    get_resource_service("archive").delete_by_article_ids([item_id])

                delete_media.assert_not_called()
                assert get_resource_service("media_references").find_one(None, item_id=item_id) is not None

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
