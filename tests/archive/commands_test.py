from superdesk.tests import TestCase
from superdesk.utc import EXPIRY_OVERFLOW_DAYS, utcnow
from apps.archive.commands import RemoveExpiredContent, SetExpiry
from datetime import datetime, timedelta
from unittest.mock import patch
from bson import ObjectId
from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE


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


class SetExpiryTestCase(TestCase):
    test_context = False

    def setUp(self):
        self.now = utcnow()
        self.desk_id = ObjectId()
        self.stage_id = ObjectId()
        self.app.data.insert("desks", [{"_id": self.desk_id, "name": "Sports News", "content_expiry": 120}])
        self.app.data.insert(
            "stages", [{"_id": self.stage_id, "desk": self.desk_id, "name": "Custom", "content_expiry": 60}]
        )

    def insert_item(
        self, item_id="test", state=CONTENT_STATE.PROGRESS, desk_id=None, stage_id=None, include_stage=True
    ):
        item = {
            "_id": item_id,
            "guid": item_id,
            "type": "text",
            "state": state,
            "task": {"desk": desk_id or self.desk_id, "stage": stage_id or self.stage_id},
            "expiry": self.now - timedelta(days=1),
            "_updated": self.now - timedelta(days=2),
            "_current_version": 7,
            "_etag": "unchanged",
        }
        if not include_stage:
            item["task"].pop("stage")
        self.app.data.insert("archive", [item])
        return get_resource_service("archive").find_one(req=None, _id=item_id)

    def assert_expiry(self, item, expiry):
        mongo_item = get_resource_service("archive").find_one(req=None, _id=item["_id"])
        elastic_item = self.app.data.elastic.find_one("archive", req=None, _id=item["_id"])
        for stored in (mongo_item, elastic_item):
            self.assertIsNotNone(stored)
            self.assertEqual(expiry, stored["expiry"])
            for key in ("_updated", "_current_version", "_etag", "state"):
                self.assertEqual(item[key], stored[key])
            self.assertEqual(
                {key: str(value) for key, value in item["task"].items()},
                {key: str(value) for key, value in stored["task"].items()},
            )

    def test_days_updates_both_stores_without_versions(self):
        item = self.insert_item()
        self.app.data.insert("archive_versions", [{"_id_document": item["_id"], "_current_version": 7}])
        versions = list(self.app.data.find_all("archive_versions"))
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            self.assertEqual(1, SetExpiry().run("Sports News", days=999))
        self.assert_expiry(item, self.now + timedelta(days=999))
        self.assertEqual(versions, list(self.app.data.find_all("archive_versions")))

    def test_config_respects_stage_desk_and_global_defaults(self):
        stage_item = self.insert_item("stage")
        desk_item = self.insert_item("desk", stage_id=ObjectId())
        global_item = self.insert_item("global", stage_id=ObjectId())
        self.app.data.insert(
            "stages",
            [
                {"_id": desk_item["task"]["stage"], "desk": self.desk_id, "name": "Desk default"},
                {"_id": global_item["task"]["stage"], "desk": self.desk_id, "name": "Global default"},
            ],
        )
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            self.assertEqual(3, SetExpiry().run("Sports News"))
        self.assert_expiry(stage_item, self.now + timedelta(minutes=60))
        self.assert_expiry(desk_item, self.now + timedelta(minutes=120))

        get_resource_service("desks").system_update(self.desk_id, {"content_expiry": None}, {"_id": self.desk_id})
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            SetExpiry().run("Sports News")
        self.assert_expiry(global_item, self.now + timedelta(minutes=self.app.settings["CONTENT_EXPIRY_MINUTES"]))

    def test_days_from_each_items_last_update(self):
        first = self.insert_item("first")
        second = self.insert_item("second")
        service = get_resource_service("archive")
        service.system_update(second["_id"], {"_updated": self.now - timedelta(days=10)}, second)
        second = service.find_one(req=None, _id=second["_id"])
        versions = list(self.app.data.find_all("archive_versions"))
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            self.assertEqual(2, SetExpiry().run("Sports News", days=5, from_updated=True))
        self.assert_expiry(first, first["_updated"] + timedelta(days=5))
        self.assert_expiry(second, second["_updated"] + timedelta(days=5))
        self.assertEqual(versions, list(self.app.data.find_all("archive_versions")))

    def test_config_from_updated_respects_stage_desk_and_global_defaults(self):
        stage_item = self.insert_item("stage")
        desk_item = self.insert_item("desk", include_stage=False)
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            self.assertEqual(2, SetExpiry().run("Sports News", from_updated=True))
        self.assert_expiry(stage_item, stage_item["_updated"] + timedelta(minutes=60))
        self.assert_expiry(desk_item, desk_item["_updated"] + timedelta(minutes=120))

        get_resource_service("desks").system_update(self.desk_id, {"content_expiry": None}, {"_id": self.desk_id})
        SetExpiry().run("Sports News", from_updated=True)
        self.assert_expiry(
            desk_item, desk_item["_updated"] + timedelta(minutes=self.app.settings["CONTENT_EXPIRY_MINUTES"])
        )

    def test_no_stage_uses_desk_config(self):
        item = self.insert_item(include_stage=False)
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            SetExpiry().run("Sports News")
        self.assert_expiry(item, self.now + timedelta(minutes=120))

    def test_disabled_expiry_clears_explicit_expiry(self):
        item = self.insert_item()
        get_resource_service("desks").system_update(self.desk_id, {"content_expiry": None}, {"_id": self.desk_id})
        get_resource_service("stages").system_update(self.stage_id, {"content_expiry": None}, {"_id": self.stage_id})
        with patch.dict(self.app.settings, {"CONTENT_EXPIRY_MINUTES": 0}):
            SetExpiry().run("Sports News")
        self.assert_expiry(item, None)

    def test_only_unpublished_workflow_items_on_selected_desk_across_batches(self):
        active_states = [
            CONTENT_STATE.DRAFT,
            CONTENT_STATE.INGESTED,
            CONTENT_STATE.ROUTED,
            CONTENT_STATE.FETCHED,
            CONTENT_STATE.SUBMITTED,
            CONTENT_STATE.PROGRESS,
        ]
        active_items = [self.insert_item("active-{}".format(state), state=state) for state in active_states]
        excluded_items = [
            self.insert_item("excluded-{}".format(state), state=state)
            for state in CONTENT_STATE
            if state not in active_states
        ]
        excluded_items.append(self.insert_item("other-desk", desk_id=ObjectId()))
        excluded_items.append(self.insert_item("unknown-state", state="unknown"))
        self.app.data.insert("published", [{"item_id": active_items[0]["_id"], "expiry": self.now}])
        published = list(self.app.data.find_all("published"))
        with patch.object(SetExpiry, "batch_size", 2), patch("apps.archive.commands.utcnow", return_value=self.now):
            self.assertEqual(len(active_states), SetExpiry().run("Sports News", days=1))
        for item in active_items:
            self.assert_expiry(item, self.now + timedelta(days=1))
        for item in excluded_items:
            self.assert_expiry(item, item["expiry"])
        self.assertEqual(published, list(self.app.data.find_all("published")))
        self.assertEqual(0, self.app.data.find_all("archive_versions").count())

    def test_unknown_desk_fails_without_updates(self):
        item = self.insert_item()
        with self.assertRaisesRegex(ValueError, "Desk not found"):
            SetExpiry().run("Missing", days=1)
        self.assert_expiry(item, item["expiry"])

    def test_invalid_days_fail_without_updates(self):
        item = self.insert_item()
        for days in (0, -1):
            with self.assertRaisesRegex(ValueError, "positive integer"):
                SetExpiry().run("Sports News", days=days)
        self.assert_expiry(item, item["expiry"])

    def test_days_above_overflow_fallback_duration(self):
        item = self.insert_item()
        with patch("apps.archive.commands.utcnow", return_value=self.now):
            self.assertEqual(1, SetExpiry().run("Sports News", days=EXPIRY_OVERFLOW_DAYS + 1))
        self.assert_expiry(item, self.now + timedelta(days=EXPIRY_OVERFLOW_DAYS + 1))

    def test_days_overflow_uses_fallback_for_both_timestamp_modes(self):
        item = self.insert_item()
        for from_updated in (False, True):
            with patch("apps.archive.commands.utcnow", return_value=self.now):
                with self.assertLogs("superdesk.utc", level="WARNING"):
                    self.assertEqual(1, SetExpiry().run("Sports News", days=10**30, from_updated=from_updated))
            base = item["_updated"] if from_updated else self.now
            self.assert_expiry(item, base + timedelta(days=EXPIRY_OVERFLOW_DAYS))

    def test_stored_expiry_overflow_uses_fallback(self):
        overflow_item = self.insert_item("overflow")
        valid = self.insert_item("valid", include_stage=False)
        get_resource_service("stages").system_update(
            self.stage_id, {"content_expiry": 9999999999999}, {"_id": self.stage_id}
        )
        with self.assertLogs("superdesk.utc", level="WARNING"):
            with patch("apps.archive.commands.utcnow", return_value=self.now):
                self.assertEqual(2, SetExpiry().run("Sports News"))
        self.assert_expiry(overflow_item, self.now + timedelta(days=EXPIRY_OVERFLOW_DAYS))
        self.assert_expiry(valid, self.now + timedelta(minutes=120))

    def test_empty_desk(self):
        self.assertEqual(0, SetExpiry().run("Sports News", days=1))

    def test_invalid_timestamps_are_logged_and_skipped_across_batches(self):
        invalid_items = [self.insert_item("invalid-{}".format(i)) for i in range(3)]
        collection = self.app.data.get_mongo_collection("archive")
        for item, value in zip(invalid_items[:2], (None, "invalid")):
            collection.update_one({"_id": item["_id"]}, {"$set": {"_updated": value}})
        collection.update_one({"_id": invalid_items[2]["_id"]}, {"$unset": {"_updated": ""}})
        valid = self.insert_item("valid")
        with patch.object(SetExpiry, "batch_size", 2), self.assertLogs("apps.archive.commands", level="ERROR") as logs:
            with patch("builtins.print") as output:
                self.assertEqual(1, SetExpiry().run("Sports News", days=5, from_updated=True))
        for item in invalid_items:
            self.assertTrue(any(item["_id"] in message for message in logs.output))
            stored = collection.find_one({"_id": item["_id"]})
            self.assertEqual(item["expiry"], stored["expiry"])
        self.assert_expiry(valid, valid["_updated"] + timedelta(days=5))
        output.assert_any_call("Skipped 3 items with expiry errors; see logs for details.")

    def test_invalid_stage_is_logged_and_skipped(self):
        invalid = self.insert_item("invalid", stage_id=ObjectId())
        valid = self.insert_item("valid")
        with self.assertLogs("apps.archive.commands", level="ERROR") as logs:
            with patch("apps.archive.commands.utcnow", return_value=self.now):
                self.assertEqual(1, SetExpiry().run("Sports News"))
        self.assertTrue(any(invalid["_id"] in message for message in logs.output))
        self.assert_expiry(invalid, invalid["expiry"])
        self.assert_expiry(valid, self.now + timedelta(minutes=60))

    def test_update_failure_is_not_reported_as_success(self):
        self.insert_item()
        with patch.object(get_resource_service("archive"), "system_update", side_effect=RuntimeError("Update failed")):
            with self.assertRaisesRegex(RuntimeError, "Update failed"):
                SetExpiry().run("Sports News", days=1)

    def test_cli_options(self):
        parser = SetExpiry().create_parser("archive:set_expiry")
        args = parser.parse_args(["--desk", "Sports News", "--days", "999"])
        self.assertEqual("Sports News", args.desk)
        self.assertEqual(999, args.days)
        self.assertFalse(args.from_updated)
        self.assertTrue(parser.parse_args(["--desk", "Sports News", "--from-updated"]).from_updated)
        self.assertIsNone(parser.parse_args(["--desk", "Sports News"]).days)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--desk", "Sports News", "--days", "invalid"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["--days", "999"])
