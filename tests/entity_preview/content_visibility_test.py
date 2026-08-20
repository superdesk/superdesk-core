from bson import ObjectId

from superdesk.entity_preview import PreviewLevel
from superdesk.entity_preview.content import content_handler, get_archive_id
from superdesk.tests import TestCase
from tests.entity_preview.fixtures import (
    ADMIN,
    DESK_A,
    DISABLED,
    GLOBAL_VIEWER,
    MEMBER_A,
    OUTSIDER,
    STAGE_A1,
    UNKNOWN,
    content_item,
    insert_content_fixtures,
)


class ContentVisibilityTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        insert_content_fixtures(self.app)

    async def can_view(self, user_id: ObjectId, item_id: str) -> bool:
        entity = await content_handler.load(item_id)
        self.assertIsNotNone(entity, item_id)
        assert entity is not None
        return await content_handler.can_view(str(user_id), entity)

    async def assertCanView(self, user_id: ObjectId, item_id: str, expected: bool):
        self.assertEqual(expected, await self.can_view(user_id, item_id), "{} / {}".format(user_id, item_id))

    async def test_load_returns_the_archive_item(self):
        entity = await content_handler.load("item_a1")
        assert entity is not None
        self.assertEqual("item_a1", entity["_id"])
        self.assertIsNone(await content_handler.load("does_not_exist"))

    async def test_load_falls_back_to_the_latest_published_version(self):
        self.app.data.insert(
            "published",
            [
                content_item(
                    "published_1",
                    ADMIN,
                    item_id="gone_from_archive",
                    state="published",
                    _current_version=2,
                    task={"desk": DESK_A, "stage": STAGE_A1},
                ),
                content_item(
                    "published_2",
                    ADMIN,
                    item_id="gone_from_archive",
                    state="corrected",
                    _current_version=3,
                    task={"desk": DESK_A, "stage": STAGE_A1},
                ),
            ],
        )

        entity = await content_handler.load("gone_from_archive")
        assert entity is not None
        self.assertEqual(3, entity["_current_version"])
        self.assertEqual("gone_from_archive", get_archive_id(entity))

        preview = await content_handler.to_preview(entity, PreviewLevel.FULL)
        self.assertEqual("gone_from_archive", preview.ref.id)
        await self.assertCanView(MEMBER_A, "gone_from_archive", True)

    async def test_desk_member_sees_content_on_their_desk(self):
        await self.assertCanView(MEMBER_A, "item_a1", True)

    async def test_desk_member_sees_content_on_an_invisible_stage_of_their_own_desk(self):
        await self.assertCanView(MEMBER_A, "item_a2", True)

    async def test_desk_member_sees_other_desks_content_because_private_filter_allows_any_non_draft(self):
        # ``private_content_filter`` ORs the per-user branch with a plain "not a draft" branch, so
        # desk membership and the global search privilege only ever matter for drafts.
        await self.assertCanView(MEMBER_A, "item_b1", True)

    async def test_desk_member_does_not_see_someone_elses_draft(self):
        await self.assertCanView(MEMBER_A, "draft_b", False)

    async def test_desk_member_sees_their_own_personal_item(self):
        await self.assertCanView(MEMBER_A, "personal_member", True)

    async def test_desk_member_does_not_see_someone_elses_personal_item(self):
        await self.assertCanView(MEMBER_A, "personal_outsider", False)

    async def test_user_without_desks_sees_desk_content_because_private_filter_allows_any_non_draft(self):
        await self.assertCanView(OUTSIDER, "item_a1", True)

    async def test_user_without_desks_sees_their_own_personal_item(self):
        await self.assertCanView(OUTSIDER, "personal_outsider", True)

    async def test_user_without_desks_does_not_see_content_on_an_invisible_stage(self):
        await self.assertCanView(OUTSIDER, "item_a2", False)

    async def test_global_viewer_sees_desk_content(self):
        await self.assertCanView(GLOBAL_VIEWER, "item_a1", True)
        await self.assertCanView(GLOBAL_VIEWER, "item_b1", True)

    async def test_global_viewer_does_not_see_an_invisible_stage_of_a_desk_they_are_not_on(self):
        await self.assertCanView(GLOBAL_VIEWER, "item_a2", False)

    async def test_global_viewer_does_not_see_someone_elses_draft(self):
        await self.assertCanView(GLOBAL_VIEWER, "draft_b", False)

    async def test_admin_sees_desk_content(self):
        await self.assertCanView(ADMIN, "item_a1", True)
        await self.assertCanView(ADMIN, "item_b1", True)

    async def test_admin_sees_their_own_draft(self):
        # ``draft_b`` was created by the admin, so it passes the "created by me" branch. Being an
        # administrator on its own does not lift the draft restriction.
        await self.assertCanView(ADMIN, "draft_b", True)

    async def test_admin_does_not_see_someone_elses_draft(self):
        await self.assertCanView(ADMIN, "personal_outsider", False)

    async def test_disabled_user_sees_nothing(self):
        await self.assertCanView(DISABLED, "item_a1", False)

    async def test_unknown_user_sees_nothing(self):
        await self.assertCanView(UNKNOWN, "item_a1", False)
