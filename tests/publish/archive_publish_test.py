import asyncio
from unittest import mock
from unittest import IsolatedAsyncioTestCase
from copy import deepcopy

from eve.utils import ParsedRequest

from apps.publish.content.common import BasePublishService
from apps.publish.content.publish import ArchivePublishService
from superdesk import get_resource_service, json
from superdesk.tests import TestCase, utils as test_utils
from superdesk.errors import SuperdeskApiError


class PublishPatchDispatchTest(IsolatedAsyncioTestCase):
    async def test_other_publish_operations_reject_scheduled_flag(self):
        service = BasePublishService()
        with mock.patch.object(service, "update_async") as update:
            await service._update_for_patch("item", {}, {}, False, allow_scheduled=False)
            update.assert_awaited_once_with("item", {}, {}, False)
            with self.assertRaises(TypeError):
                await service._update_for_patch("item", {}, {}, False, allow_scheduled=True)
            update.assert_awaited_once()

    async def test_scheduled_association_is_not_published_again(self):
        service = ArchivePublishService()
        archive = mock.Mock()
        archive.find_one_async = mock.AsyncMock(
            return_value={"_id": "image", "state": "scheduled", "operation": "publish"}
        )
        publish = mock.Mock()
        publish.patch_async = mock.AsyncMock()

        with (
            mock.patch("apps.publish.content.common.get_config", return_value=True),
            mock.patch(
                "apps.publish.content.common.get_resource_service",
                side_effect=lambda name: {"archive": archive, "archive_publish": publish}[name],
            ),
            mock.patch.object(service, "_refresh_associated_items"),
        ):
            for has_updates in (False, True):
                with self.subTest(has_updates=has_updates):
                    image = {"_id": "image", "state": "scheduled", "operation": "publish"}
                    original = {"associations": {"media--1": image}}
                    updates = {"state": "scheduled"}
                    if has_updates:
                        updates["associations"] = {"media--1": image.copy()}
                    await service._publish_associated_items(original, updates)
                    publish.patch_async.assert_not_awaited()


class MockAutosaveComponent:
    async def clear(self, item_id):
        raise Exception("Mock autosave component error")


class ArchivePublishTest(TestCase):
    async def test_publish_lock_rejects_concurrent_requests(self):
        archive = get_resource_service("archive")
        published = get_resource_service("published")
        service = get_resource_service("archive_publish")
        process_item = service._process_item_updates_and_associations

        item_id = "concurrent-immediate"
        item = {
            "_id": item_id,
            "guid": item_id,
            "unique_name": item_id,
            "type": "text",
            "state": "submitted",
            "headline": "Concurrent publish",
            "_current_version": 1,
        }
        await archive.create_async([item])
        entered = asyncio.Event()
        release = asyncio.Event()

        async def pause_first_publish(original, changes):
            if not entered.is_set():
                entered.set()
                await release.wait()
            return await process_item(original, changes)

        with mock.patch.object(
            service, "_process_item_updates_and_associations", side_effect=pause_first_publish
        ) as process:
            async with asyncio.TaskGroup() as requests:
                first_request = requests.create_task(service.patch_async(item_id, {}))
                await asyncio.wait_for(entered.wait(), timeout=5)
                with self.assertRaises(SuperdeskApiError) as error:
                    await asyncio.wait_for(service.patch_async(item_id, {}), timeout=5)
                self.assertEqual(error.exception.status_code, 409)
                self.assertEqual(error.exception.message, "This article is already being published.")
                self.assertFalse(first_request.done())
                process.assert_awaited_once()
                release.set()
                await asyncio.wait_for(first_request, timeout=5)

        published_items = await published.get_from_mongo_async(req=None, lookup={"item_id": item_id})
        self.assertEqual(await published_items.count(), 1)
        stored_item = await archive.find_one_async(req=None, _id=item_id)
        self.assertEqual(stored_item["state"], "published")
        self.assertEqual(stored_item["_current_version"], 2)

    async def test_rejected_scheduled_publish_does_not_change_media_usage(self):
        archive = get_resource_service("archive")
        article = {
            "_id": "scheduled-article",
            "guid": "scheduled-article",
            "type": "text",
            "state": "scheduled",
            "headline": "Scheduled article",
            "_current_version": 1,
        }
        image = {
            "_id": "new-image",
            "guid": "new-image",
            "type": "picture",
            "state": "in_progress",
            "headline": "New image",
            "_current_version": 1,
            "used": False,
            "used_count": 0,
        }
        await archive.create_async([article, image])
        original_image = await archive.find_one_async(req=None, _id=image["_id"])

        for _ in range(2):
            with self.assertRaises(SuperdeskApiError) as error:
                await get_resource_service("archive_publish").patch_async(
                    article["_id"], {"associations": {"featuremedia": deepcopy(original_image)}}
                )
            self.assertEqual(error.exception.status_code, 409)
            self.assertIn("already scheduled", error.exception.message)
            self.assertEqual(original_image, await archive.find_one_async(req=None, _id=image["_id"]))
            stored_article = await archive.find_one_async(req=None, _id=article["_id"])
            self.assertFalse(stored_article.get("associations"))

    @mock.patch("apps.publish.content.common.get_component", return_value=MockAutosaveComponent())
    async def test_published_item_exists_when_publish_exception_raised(self, _mock):
        # First, create the Desk and content for us to publish/test against
        desk = {"name": "sports"}
        await test_utils.post_items("desks", [desk])
        item = {
            "_id": "foo",
            "guid": "foo",
            "unique_name": "foo",
            "type": "text",
            "_current_version": 2,
            "state": "submitted",
            "headline": "foo",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
        }
        await get_resource_service("archive").create_async([item])

        async def get_search_count(repos: str) -> int:
            req = ParsedRequest()
            req.args = {"source": json.dumps({"query": {"bool": {}}}), "repo": repos}
            cursor = await get_resource_service("search").get_async(req=req, lookup=None)
            return await cursor.count()

        # Next up, test the item can be found in the "archive" search repo and not in "published"
        self.assertEqual(1, await get_search_count("archive,published"))
        self.assertEqual(1, await get_search_count("archive"))
        self.assertEqual(0, await get_search_count("published"))

        # Now, publish the item (making sure that the MockAutosave exception is raised)
        with self.assertRaises(SuperdeskApiError):
            await get_resource_service("archive_publish").patch_async(item["_id"], {})

        # Finally, test the item can be found in the "published" search repo and not in "archive"
        self.assertEqual(1, await get_search_count("archive,published"))
        self.assertEqual(0, await get_search_count("archive"))
        self.assertEqual(1, await get_search_count("published"))
