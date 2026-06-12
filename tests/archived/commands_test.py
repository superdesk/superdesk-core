from bson import ObjectId
from superdesk.tests import TestCase, utils as test_utils
from apps.archived.commands import UnarchiveItemCommand


class UnarchiveItemCommandTestCase(TestCase):
    async def test_unarchive_single_item(self):
        await test_utils.post_items(
            "archived",
            [
                {
                    "_id": ObjectId(),
                    "item_id": "test",
                    "guid": "test",
                    "type": "text",
                    "state": "published",
                }
            ],
        )
        await UnarchiveItemCommand().run(["test"])
        assert await test_utils.count("archived", {"item_id": "test"}) == 0
        assert await test_utils.count("archive", {"_id": "test"}) == 1
        assert await test_utils.count("published", {"item_id": "test"}) == 1

    async def test_unarchive_package_restores_children(self):
        package_id = "package"
        picture_id = "picture"
        text_id = "text"

        await test_utils.post_items(
            "archived",
            [
                {
                    "_id": ObjectId(),
                    "item_id": picture_id,
                    "guid": picture_id,
                    "type": "picture",
                    "state": "published",
                    "headline": "Picture",
                },
                {
                    "_id": ObjectId(),
                    "item_id": text_id,
                    "guid": text_id,
                    "type": "text",
                    "state": "published",
                    "headline": "Text",
                },
                {
                    "_id": ObjectId(),
                    "item_id": package_id,
                    "guid": package_id,
                    "type": "composite",
                    "state": "published",
                    "headline": "Package",
                    "groups": [
                        {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                        {
                            "id": "main",
                            "refs": [
                                {"residRef": picture_id, "location": "archive"},
                                {"residRef": text_id, "location": "archive"},
                            ],
                            "role": "grpRole:main",
                        },
                    ],
                },
            ],
        )

        await UnarchiveItemCommand().run([package_id])

        assert await test_utils.count("archived", {"item_id": package_id}) == 0
        assert await test_utils.count("archived", {"item_id": picture_id}) == 0
        assert await test_utils.count("archived", {"item_id": text_id}) == 0
        assert await test_utils.count("archive", {"_id": package_id}) == 1
        assert await test_utils.count("archive", {"_id": picture_id}) == 1
        assert await test_utils.count("archive", {"_id": text_id}) == 1
        assert await test_utils.count("published", {"item_id": package_id}) == 1
        assert await test_utils.count("published", {"item_id": picture_id}) == 1
        assert await test_utils.count("published", {"item_id": text_id}) == 1

    async def test_unarchive_dry_run(self):
        await test_utils.post_items(
            "archived",
            [
                {
                    "_id": ObjectId(),
                    "item_id": "dry",
                    "guid": "dry",
                    "type": "text",
                    "state": "published",
                }
            ],
        )
        await UnarchiveItemCommand().run(["dry"], dry_run=True)
        assert await test_utils.count("archived", {"item_id": "dry"}) == 1
        assert await test_utils.count("archive", {"_id": "dry"}) == 0

    async def test_unarchive_collision_aborts(self):
        await test_utils.post_items(
            "archived",
            [
                {
                    "_id": ObjectId(),
                    "item_id": "coll",
                    "guid": "coll",
                    "type": "text",
                    "state": "published",
                }
            ],
        )
        await test_utils.post_items("archive", [{"_id": "coll", "type": "text", "state": "published"}])
        results = await UnarchiveItemCommand().run(["coll"])
        assert len(results["failed"]) == 1
        assert await test_utils.count("archived", {"item_id": "coll"}) == 1
