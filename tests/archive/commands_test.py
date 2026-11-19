from unittest.mock import patch
from datetime import datetime, timedelta

from bson import ObjectId

from superdesk.tests import TestCase, utils as test_utils
from superdesk.utc import utcnow
from apps.archive.commands import RemoveExpiredContent
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from celery.exceptions import SoftTimeLimitExceeded


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

    async def test_archived_expiry_preserves_production_item_and_media(self):
        protected_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        expired_id = ObjectId.from_datetime(datetime(2024, 1, 2))
        await test_utils.post_items("archive", [{"_id": "protected", "type": "picture"}])

        for legal_archive in (True, False):
            with self.subTest(legal_archive=legal_archive):
                settings = {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": legal_archive}
                await test_utils.post_items(
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
                        await RemoveExpiredContent()._remove_expired_archived_items(utcnow())

                assert await test_utils.count("archived") == 0
                assert await test_utils.find_one("archive", _id="protected") is not None
                assert {call.kwargs["item"]["_id"] for call in removed_signal.call_args_list} == {
                    protected_id,
                    expired_id,
                }
                if legal_archive:
                    remove_media.assert_not_called()
                else:
                    remove_media.assert_called_once()
                    assert remove_media.call_args.args[0]["item_id"] == "expired"

    async def test_production_delete_cleans_media_retained_after_archived_expiry(self):
        await self._assert_retained_media_cleanup(keep_newer_snapshot=False)

    async def test_final_archived_expiry_cleans_media_retained_from_older_snapshot(self):
        await self._assert_retained_media_cleanup(keep_newer_snapshot=True)

    async def test_production_delete_preserves_media_used_by_unpublished_duplicate(self):
        item_id = "expired-original"
        duplicate_id = "surviving-duplicate"
        media_id = "shared-media"
        archived_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        await test_utils.post_items(
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
        await test_utils.post_items(
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
        await test_utils.post_items(
            "media_references",
            [
                {"item_id": item_id, "media_id": media_id, "published": True},
                {"item_id": duplicate_id, "media_id": media_id, "published": False},
            ],
        )

        with (
            patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": False}),
            patch.object(self.app.media, "delete_async") as delete_media,
        ):
            await RemoveExpiredContent()._remove_expired_archived_items(utcnow())

            assert await test_utils.find_one("archived", _id=archived_id) is None
            assert await test_utils.find_one("media_references", item_id=item_id, media_id=media_id, published=True)

            await get_resource_service("archive").delete_by_article_ids([item_id])

        assert await test_utils.find_one("archive", _id=duplicate_id) is not None
        assert await test_utils.find_one("media_references", item_id=duplicate_id, media_id=media_id, published=False)
        delete_media.assert_not_called()

    async def _assert_retained_media_cleanup(self, keep_newer_snapshot):
        item_id = "deferred-media"
        item_guid = "external-media-guid"
        archived_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        newer_id = ObjectId()
        await test_utils.post_items(
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
        await test_utils.post_items(
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
            await test_utils.post_items(
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
        await test_utils.post_items(
            "media_references",
            [
                {"item_id": item_id, "media_id": media_id, "published": True}
                for media_id in ("current-media", "old-media", "shared-media")
            ]
            + [{"item_id": "other-item", "media_id": "shared-media", "published": True}],
        )
        with (
            patch.dict(self.app.config, {"ARCHIVED_EXPIRY_MINUTES": 1, "LEGAL_ARCHIVE": False}),
            patch.object(self.app.media, "delete_async") as delete_media,
        ):
            await RemoveExpiredContent()._remove_expired_archived_items(utcnow())

            assert await test_utils.find_one("archived", _id=archived_id) is None
            assert await test_utils.count("media_references", {"item_id": item_id}) == 3
            delete_media.assert_not_called()

            await get_resource_service("archive").delete_by_article_ids([item_id])

            if keep_newer_snapshot:
                assert await test_utils.find_one("archive", _id=item_id) is None
                assert await test_utils.find_one("archived", _id=newer_id) is not None
                assert await test_utils.count("media_references", {"item_id": item_id}) == 3
                delete_media.assert_not_called()

                await RemoveExpiredContent()._remove_expired_archived_items(utcnow() + timedelta(minutes=2))

        assert await test_utils.find_one("archive", _id=item_id) is None
        assert await test_utils.find_one("archived", item_id=item_id) is None
        assert await test_utils.count("media_references", {"item_id": item_id}) == 0
        assert await test_utils.find_one("media_references", item_id="other-item", media_id="shared-media")
        self.assertCountEqual(
            ["current-media", "old-media"],
            [call.args[0] for call in delete_media.call_args_list],
        )

    async def test_archive_version_cleanup_uses_production_id_instead_of_version_id_or_guid(self):
        item_id = "version-production-id"
        version_id = ObjectId()
        await test_utils.post_items(
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
        await test_utils.post_items(
            "media_references",
            [
                {"item_id": item_id, "media_id": "version-media", "published": True},
                {"item_id": item_id, "media_id": "unpublished-media", "published": False},
            ],
        )
        with (
            patch.dict(self.app.config, {"LEGAL_ARCHIVE": False}),
            patch.object(self.app.media, "delete_async") as delete_media,
        ):
            await get_resource_service("archive_versions").delete_action_async({"_id": version_id})

        assert await test_utils.find_one("archive_versions", _id=version_id) is None
        assert await test_utils.count("media_references", {"item_id": item_id}) == 0
        self.assertCountEqual(
            ["version-media", "unpublished-media"],
            [call.args[0] for call in delete_media.call_args_list],
        )

    async def test_production_delete_retains_media_needed_by_other_repositories(self):
        for repository in ("archived", "published", "legal_archive"):
            with self.subTest(repository=repository):
                item_id = "retained-" + repository
                await test_utils.post_items(
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
                    # published items take their item_id from the production item's _id
                    doc = {"_id": item_id} if repository == "published" else {"item_id": item_id}
                    await test_utils.post_items(
                        repository, [{**doc, "guid": item_id, "type": "picture", "state": "published"}]
                    )
                await test_utils.post_items(
                    "media_references",
                    [{"item_id": item_id, "media_id": item_id, "published": True}],
                )
                with (
                    patch.dict(self.app.config, {"LEGAL_ARCHIVE": repository == "legal_archive"}),
                    patch.object(self.app.media, "delete_async") as delete_media,
                ):
                    await get_resource_service("archive").delete_by_article_ids([item_id])

                delete_media.assert_not_called()
                assert await test_utils.find_one("media_references", item_id=item_id) is not None

    async def test_normal_archived_delete_still_validates_production_item(self):
        await test_utils.post_items("archive", [{"_id": "protected", "type": "picture"}])
        item = {
            "_id": ObjectId.from_datetime(datetime(2024, 1, 1)),
            "item_id": "protected",
            "guid": "protected",
            "type": "picture",
        }
        await test_utils.post_items("archived", [item])

        with self.assertRaises(SuperdeskApiError):
            await get_resource_service("archived").delete_docs_async([item.copy()])

        assert await test_utils.count("archived") == 1

    async def test_archived_cleanup_failure_does_not_block_remaining_items(self):
        first_id = ObjectId.from_datetime(datetime(2024, 1, 1))
        second_id = ObjectId.from_datetime(datetime(2024, 1, 2))
        for failure in ("signal", "media"):
            with self.subTest(failure=failure):
                await test_utils.post_items(
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
                    await RemoveExpiredContent()._remove_expired_archived_items(utcnow())

                assert await test_utils.count("archived") == 0
                assert removed_signal.call_count == 2
                assert remove_media.call_args.args[0]["item_id"] == "second"
                assert str(first_id) in logs.output[0]
                assert "item_id=first" in logs.output[0]

    async def test_archived_cleanup_does_not_swallow_soft_time_limit(self):
        await test_utils.post_items(
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
            await RemoveExpiredContent()._remove_expired_archived_items(utcnow())
