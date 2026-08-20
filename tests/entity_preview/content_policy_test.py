import json

from datetime import timedelta

from bson import ObjectId

from superdesk.entity_preview import PreviewLevel
from superdesk.entity_preview.content import ALLOWED_SOURCE_FIELDS, content_handler
from superdesk.slack.render import render_preview
from superdesk.tests import TestCase
from superdesk.utc import utcnow


CLIENT_URL = "https://news.example.com"
DESK_ID = ObjectId("5c1f2c1f2c1f2c1f2c1f2c1f")
STAGE_ID = ObjectId("5c1f2c1f2c1f2c1f2c1f2c20")
USER_ID = ObjectId("5c1f2c1f2c1f2c1f2c1f2c21")

SECRETS = {
    "body_html": "<p>the whole story body</p>",
    "abstract": "the secret abstract",
    "description_text": "the secret description",
    "ednote": "do not publish before checking with legal",
    "sms_message": "sms only text",
}


def item(**overrides) -> dict:
    doc = {
        "_id": "item1",
        "type": "text",
        "state": "in_progress",
        "headline": "Headline of the item",
        "slugline": "the-slugline",
        "versioncreated": utcnow(),
        "task": {"desk": DESK_ID, "stage": STAGE_ID},
        "original_creator": USER_ID,
    }
    doc.update(overrides)
    return doc


class ContentPolicyTestCase(TestCase):
    app_config = {"CLIENT_URL": CLIENT_URL}

    def assertLevel(self, expected: PreviewLevel, doc: dict):
        self.assertEqual(expected, content_handler.policy(doc))

    async def test_normal_item_is_full(self):
        self.assertLevel(PreviewLevel.FULL, item())

    async def test_missing_flags_is_full(self):
        self.assertLevel(PreviewLevel.FULL, item(flags=None))

    async def test_future_embargo_is_generic(self):
        self.assertLevel(PreviewLevel.GENERIC, item(embargo=utcnow() + timedelta(hours=2)))

    async def test_future_utc_embargo_from_schedule_settings_is_generic(self):
        doc = item(schedule_settings={"utc_embargo": utcnow() + timedelta(hours=2), "time_zone": "Europe/Prague"})
        self.assertLevel(PreviewLevel.GENERIC, doc)

    async def test_future_embargo_as_string_is_generic(self):
        doc = item(embargo=(utcnow() + timedelta(hours=2)).isoformat())
        self.assertLevel(PreviewLevel.GENERIC, doc)

    async def test_naive_future_embargo_is_treated_as_utc(self):
        doc = item(embargo=(utcnow() + timedelta(hours=2)).replace(tzinfo=None))
        self.assertLevel(PreviewLevel.GENERIC, doc)

    async def test_past_embargo_is_full(self):
        self.assertLevel(PreviewLevel.FULL, item(embargo=utcnow() - timedelta(hours=2)))

    async def test_unparsable_embargo_is_full(self):
        self.assertLevel(PreviewLevel.FULL, item(embargo="not a date"))

    async def test_marked_for_legal_is_generic(self):
        self.assertLevel(PreviewLevel.GENERIC, item(flags={"marked_for_legal": True}))

    async def test_marked_for_not_publication_is_generic(self):
        self.assertLevel(PreviewLevel.GENERIC, item(flags={"marked_for_not_publication": True}))

    async def test_spiked_killed_and_recalled_are_generic(self):
        for state in ("spiked", "killed", "recalled"):
            self.assertLevel(PreviewLevel.GENERIC, item(state=state))


class ContentPreviewTestCase(TestCase):
    app_config = {"CLIENT_URL": CLIENT_URL}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.data.insert("desks", [{"_id": DESK_ID, "name": "Sports desk"}])
        self.app.data.insert("stages", [{"_id": STAGE_ID, "name": "Working stage", "desk": DESK_ID}])
        self.app.data.insert(
            "users",
            [
                {
                    "_id": USER_ID,
                    "username": "creator",
                    "first_name": "Jane",
                    "last_name": "Creator",
                    "is_active": True,
                    "is_enabled": True,
                    "user_type": "user",
                }
            ],
        )

    async def test_full_preview(self):
        doc = item(versioncreated=utcnow())
        preview = await content_handler.to_preview(doc, PreviewLevel.FULL)

        self.assertEqual(PreviewLevel.FULL, preview.level)
        self.assertEqual("content", preview.ref.type)
        self.assertEqual("item1", preview.ref.id)
        self.assertEqual("Headline of the item", preview.title)
        self.assertEqual("Text story", preview.type_label)
        self.assertEqual("In progress", preview.status)
        self.assertEqual(doc["versioncreated"], preview.updated)
        self.assertEqual(f"{CLIENT_URL}/#/workspace?item=item1&action=view", preview.url)
        self.assertEqual(
            [
                ("Desk", "Sports desk"),
                ("Stage", "Working stage"),
                ("Author", "Jane Creator"),
                ("Slugline", "the-slugline"),
            ],
            preview.fields,
        )

    async def test_title_falls_back_to_slugline_then_untitled(self):
        preview = await content_handler.to_preview(item(headline=""), PreviewLevel.FULL)
        self.assertEqual("the-slugline", preview.title)
        self.assertNotIn("Slugline", dict(preview.fields))

        preview = await content_handler.to_preview(item(headline="", slugline=""), PreviewLevel.FULL)
        self.assertEqual("Untitled", preview.title)

    async def test_author_prefers_authors_then_byline(self):
        preview = await content_handler.to_preview(
            item(authors=[{"name": "Ann Author", "role": "writer"}], byline="Bob Byline"), PreviewLevel.FULL
        )
        self.assertEqual("Ann Author", dict(preview.fields)["Author"])

        preview = await content_handler.to_preview(item(byline="Bob Byline"), PreviewLevel.FULL)
        self.assertEqual("Bob Byline", dict(preview.fields)["Author"])

    async def test_type_and_status_labels(self):
        preview = await content_handler.to_preview(item(type="picture", state="being_corrected"), PreviewLevel.FULL)
        self.assertEqual("Picture", preview.type_label)
        self.assertEqual("Being corrected", preview.status)

        preview = await content_handler.to_preview(item(type="composite", state="published"), PreviewLevel.FULL)
        self.assertEqual("Package", preview.type_label)
        self.assertEqual("Published", preview.status)

        preview = await content_handler.to_preview(item(type="newtype", state="some_new_state"), PreviewLevel.FULL)
        self.assertEqual("Newtype", preview.type_label)
        self.assertEqual("Some new state", preview.status)

    async def test_published_item_preview_uses_the_archive_id(self):
        doc = item(_id=ObjectId("5c1f2c1f2c1f2c1f2c1f2c22"), item_id="archive-id", state="published")
        preview = await content_handler.to_preview(doc, PreviewLevel.FULL)
        self.assertEqual("archive-id", preview.ref.id)
        self.assertEqual(f"{CLIENT_URL}/#/workspace?item=archive-id&action=view", preview.url)

    async def test_full_preview_never_leaks_restricted_fields(self):
        doc = item(
            embargo=utcnow() - timedelta(hours=2),
            lock_user=USER_ID,
            lock_session="session-id",
            flags={"marked_for_legal": False},
            associations={"featuremedia": {"headline": "secret picture"}},
            subscribers=["secret-subscriber"],
            **SECRETS,
        )
        preview = await content_handler.to_preview(doc, PreviewLevel.FULL)
        rendered = json.dumps(render_preview(preview))

        for value in SECRETS.values():
            self.assertNotIn(value, rendered)
        self.assertNotIn("secret picture", rendered)
        self.assertNotIn("secret-subscriber", rendered)
        self.assertNotIn("session-id", rendered)
        self.assertNotIn(doc["embargo"].isoformat(), rendered)

    async def test_allow_list_excludes_the_restricted_fields(self):
        restricted = (
            "body_html",
            "abstract",
            "description_text",
            "ednote",
            "embargo",
            "publish_schedule",
            "schedule_settings",
            "flags",
            "lock_user",
            "lock_session",
            "sms_message",
            "associations",
            "subscribers",
            "targets",
        )
        for name in restricted:
            self.assertNotIn(name, ALLOWED_SOURCE_FIELDS)

    async def test_generic_preview_hides_everything_but_the_type(self):
        doc = item(state="spiked")
        preview = await content_handler.to_preview(doc, PreviewLevel.GENERIC)

        self.assertEqual("Superdesk content item", preview.title)
        self.assertEqual("Text story", preview.type_label)
        self.assertEqual([], preview.fields)
        self.assertIsNone(preview.status)
        self.assertIsNone(preview.updated)
        self.assertEqual(f"{CLIENT_URL}/#/workspace?item=item1&action=view", preview.url)

        rendered = json.dumps(render_preview(preview))
        self.assertNotIn("Headline of the item", rendered)
        self.assertNotIn("the-slugline", rendered)
        self.assertNotIn("Sports desk", rendered)
        self.assertNotIn("spiked", rendered)
