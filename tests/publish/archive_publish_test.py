from unittest import mock
from unittest import IsolatedAsyncioTestCase

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
