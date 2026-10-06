from superdesk.tests import TestCase
from superdesk.utc import EXPIRY_OVERFLOW_DAYS, utcnow
from apps.archive.set_expiry import SetExpiry
from datetime import timedelta
from unittest.mock import patch
from bson import ObjectId
from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE
from superdesk import COMMANDS


class SetExpiryTestCase(TestCase):
    test_context = False

    def setUp(self):
        self.now = utcnow()
        clock = patch("apps.archive.set_expiry.utcnow", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)
        backend_clock = patch("superdesk.eve_backend.utcnow", return_value=self.now)
        backend_clock.start()
        self.addCleanup(backend_clock.stop)
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

    def assert_expiry(self, item, expiry, updated=True):
        mongo_item = get_resource_service("archive").find_one(req=None, _id=item["_id"])
        elastic_item = self.app.data.elastic.find_one("archive", req=None, _id=item["_id"])
        for stored in (mongo_item, elastic_item):
            self.assertIsNotNone(stored)
            self.assertEqual(expiry, stored["expiry"])
            self.assertEqual(self.now if updated else item["_updated"], stored["_updated"])
            for key in ("_current_version", "_etag", "state"):
                self.assertEqual(item[key], stored[key])
            self.assertEqual(
                {key: str(value) for key, value in item["task"].items()},
                {key: str(value) for key, value in stored["task"].items()},
            )

    def test_days_updates_both_stores_without_versions(self):
        item = self.insert_item()
        self.app.data.insert("archive_versions", [{"_id_document": item["_id"], "_current_version": 7}])
        versions = list(self.app.data.find_all("archive_versions"))
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
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
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            self.assertEqual(3, SetExpiry().run("Sports News"))
        self.assert_expiry(stage_item, self.now + timedelta(minutes=60))
        self.assert_expiry(desk_item, self.now + timedelta(minutes=120))

        get_resource_service("desks").system_update(self.desk_id, {"content_expiry": None}, {"_id": self.desk_id})
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            SetExpiry().run("Sports News")
        self.assert_expiry(global_item, self.now + timedelta(minutes=self.app.settings["CONTENT_EXPIRY_MINUTES"]))

    def test_days_from_each_items_last_update(self):
        first = self.insert_item("first")
        second = self.insert_item("second")
        service = get_resource_service("archive")
        service.system_update(second["_id"], {"_updated": self.now - timedelta(days=10)}, second)
        second = service.find_one(req=None, _id=second["_id"])
        versions = list(self.app.data.find_all("archive_versions"))
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            self.assertEqual(2, SetExpiry().run("Sports News", days=5, from_updated=True))
        self.assert_expiry(first, first["_updated"] + timedelta(days=5))
        self.assert_expiry(second, second["_updated"] + timedelta(days=5))
        self.assertEqual(versions, list(self.app.data.find_all("archive_versions")))

    def test_config_from_updated_respects_stage_desk_and_global_defaults(self):
        stage_item = self.insert_item("stage")
        desk_item = self.insert_item("desk", include_stage=False)
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            self.assertEqual(2, SetExpiry().run("Sports News", from_updated=True))
        self.assert_expiry(stage_item, stage_item["_updated"] + timedelta(minutes=60))
        self.assert_expiry(desk_item, desk_item["_updated"] + timedelta(minutes=120))

        get_resource_service("desks").system_update(self.desk_id, {"content_expiry": None}, {"_id": self.desk_id})
        desk_item = get_resource_service("archive").find_one(req=None, _id=desk_item["_id"])
        SetExpiry().run("Sports News", from_updated=True)
        self.assert_expiry(
            desk_item, desk_item["_updated"] + timedelta(minutes=self.app.settings["CONTENT_EXPIRY_MINUTES"])
        )

    def test_no_stage_uses_desk_config(self):
        item = self.insert_item(include_stage=False)
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            SetExpiry().run("Sports News")
        self.assert_expiry(item, self.now + timedelta(minutes=120))

    def test_desk_and_stage_reads_are_cached_across_batches_with_item_offsets(self):
        other_stage = ObjectId()
        self.app.data.insert(
            "stages", [{"_id": other_stage, "desk": self.desk_id, "name": "Other", "content_expiry": 180}]
        )
        items = [
            self.insert_item("item-{}".format(i), stage_id=other_stage if i == 3 else self.stage_id) for i in range(5)
        ]
        collection = self.app.data.get_mongo_collection("archive")
        for i, item in enumerate(items):
            item["_updated"] = self.now - timedelta(days=i + 1)
            collection.update_one({"_id": item["_id"]}, {"$set": {"_updated": item["_updated"]}})
        desks = get_resource_service("desks")
        stages = get_resource_service("stages")
        with patch.object(desks, "find_one", wraps=desks.find_one) as desk_read:
            with patch.object(stages, "find_one", wraps=stages.find_one) as stage_read:
                with patch.object(SetExpiry, "batch_size", 2):
                    self.assertEqual(5, SetExpiry().run("Sports News", from_updated=True))
        desk_read.assert_called_once_with(req=None, name="Sports News")
        self.assertEqual(2, stage_read.call_count)
        stage_read.assert_any_call(req=None, _id=self.stage_id)
        stage_read.assert_any_call(req=None, _id=other_stage)
        for i, item in enumerate(items):
            self.assert_expiry(item, item["_updated"] + timedelta(minutes=180 if i == 3 else 60))

    def test_missing_stage_is_cached_and_each_item_is_skipped(self):
        missing_stage = ObjectId()
        invalid = [self.insert_item("invalid-{}".format(i), stage_id=missing_stage) for i in range(3)]
        valid = self.insert_item("valid", include_stage=False)
        stages = get_resource_service("stages")
        with patch.object(stages, "find_one", wraps=stages.find_one) as stage_read:
            with patch.object(SetExpiry, "batch_size", 1):
                with self.assertLogs("apps.archive.set_expiry", level="ERROR") as logs:
                    self.assertEqual(1, SetExpiry().run("Sports News"))
        stage_read.assert_called_once_with(req=None, _id=missing_stage)
        self.assertEqual(3, len(logs.output))
        for item in invalid:
            self.assertTrue(
                any(item["_id"] in message and "Invalid stage identifier" in message for message in logs.output)
            )
            self.assert_expiry(item, item["expiry"], updated=False)
        self.assert_expiry(valid, self.now + timedelta(minutes=120))

    def test_days_does_not_fetch_stages(self):
        item = self.insert_item(stage_id=ObjectId())
        stages = get_resource_service("stages")
        with patch.object(stages, "find_one", wraps=stages.find_one) as stage_read:
            self.assertEqual(1, SetExpiry().run("Sports News", days=1))
        stage_read.assert_not_called()
        self.assert_expiry(item, self.now + timedelta(days=1))

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
        with patch.object(SetExpiry, "batch_size", 2), patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            self.assertEqual(len(active_states), SetExpiry().run("Sports News", days=1))
        for item in active_items:
            self.assert_expiry(item, self.now + timedelta(days=1))
        for item in excluded_items:
            self.assert_expiry(item, item["expiry"], updated=False)
        self.assertEqual(published, list(self.app.data.find_all("published")))
        self.assertEqual(0, self.app.data.find_all("archive_versions").count())

    def test_unknown_desk_fails_without_updates(self):
        item = self.insert_item()
        with self.assertRaisesRegex(ValueError, "Desk not found"):
            SetExpiry().run("Missing", days=1)
        self.assert_expiry(item, item["expiry"], updated=False)

    def test_invalid_days_fail_without_updates(self):
        item = self.insert_item()
        for days in (0, -1):
            with self.assertRaisesRegex(ValueError, "positive integer"):
                SetExpiry().run("Sports News", days=days)
        self.assert_expiry(item, item["expiry"], updated=False)

    def test_days_above_overflow_fallback_duration(self):
        item = self.insert_item()
        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
            self.assertEqual(1, SetExpiry().run("Sports News", days=EXPIRY_OVERFLOW_DAYS + 1))
        self.assert_expiry(item, self.now + timedelta(days=EXPIRY_OVERFLOW_DAYS + 1))

    def test_days_overflow_uses_fallback_for_both_timestamp_modes(self):
        for from_updated in (False, True):
            item = self.insert_item("overflow-{}".format(from_updated))
            with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
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
            with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
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
        with patch.object(SetExpiry, "batch_size", 2), self.assertLogs(
            "apps.archive.set_expiry", level="ERROR"
        ) as logs:
            with patch("builtins.print") as output:
                self.assertEqual(1, SetExpiry().run("Sports News", days=5, from_updated=True))
        for item in invalid_items:
            self.assertTrue(any(item["_id"] in message for message in logs.output))
            stored = collection.find_one({"_id": item["_id"]})
            self.assertEqual(item["expiry"], stored["expiry"])
        self.assert_expiry(valid, valid["_updated"] + timedelta(days=5))
        output.assert_any_call("Skipped 3 items with expiry errors; see logs for details.")

    def test_now_mode_accepts_invalid_or_missing_updated_timestamps(self):
        items = [self.insert_item("invalid-{}".format(i)) for i in range(3)]
        collection = self.app.data.get_mongo_collection("archive")
        for item, value in zip(items[:2], (None, "invalid")):
            collection.update_one({"_id": item["_id"]}, {"$set": {"_updated": value}})
        collection.update_one({"_id": items[2]["_id"]}, {"$unset": {"_updated": ""}})
        self.assertEqual(3, SetExpiry().run("Sports News", days=5))
        for item in items:
            self.assert_expiry(item, self.now + timedelta(days=5))

    def test_invalid_stage_is_logged_and_skipped(self):
        invalid = self.insert_item("invalid", stage_id=ObjectId())
        valid = self.insert_item("valid")
        with self.assertLogs("apps.archive.set_expiry", level="ERROR") as logs:
            with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
                self.assertEqual(1, SetExpiry().run("Sports News"))
        self.assertTrue(any(invalid["_id"] in message for message in logs.output))
        self.assert_expiry(invalid, invalid["expiry"], updated=False)
        self.assert_expiry(valid, self.now + timedelta(minutes=60))

    def test_update_failure_is_not_reported_as_success(self):
        self.insert_item()
        collection = self.app.data.get_mongo_collection("archive")
        with patch.object(self.app.data.mongo, "get_collection_with_write_concern", return_value=collection):
            with patch.object(collection, "update_one", side_effect=RuntimeError("Update failed")):
                with self.assertRaisesRegex(RuntimeError, "Update failed"):
                    SetExpiry().run("Sports News", days=1)

    def assert_concurrent_change_skipped(self, changes=None, remove=False):
        changed = self.insert_item("changed")
        valid = self.insert_item("valid")
        collection = self.app.data.get_mongo_collection("archive")
        update_one = collection.update_one

        def concurrent_update(query, update):
            if query["_id"] == changed["_id"]:
                if remove:
                    collection.delete_one({"_id": changed["_id"]})
                else:
                    update_one({"_id": changed["_id"]}, {"$set": changes})
            return update_one(query, update)

        with patch.object(self.app.data.mongo, "get_collection_with_write_concern", return_value=collection):
            with patch.object(collection, "update_one", side_effect=concurrent_update):
                with patch.object(self.app.data.elastic, "update", wraps=self.app.data.elastic.update) as index:
                    with self.assertLogs("apps.archive.set_expiry", level="WARNING") as logs:
                        with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
                            with patch("builtins.print") as output:
                                self.assertEqual(1, SetExpiry().run("Sports News", days=5))
        self.assertTrue(any(changed["_id"] in message for message in logs.output))
        output.assert_any_call("Skipped 1 items changed or removed concurrently; see logs for details.")
        self.assertEqual(1, index.call_count)
        self.assertEqual(valid["_id"], index.call_args.args[1])
        self.assert_expiry(valid, self.now + timedelta(days=5))
        stored = collection.find_one({"_id": changed["_id"]})
        if remove:
            self.assertIsNone(stored)
        else:
            self.assertEqual(changes.get("expiry", changed["expiry"]), stored["expiry"])
            for key, value in changes.items():
                self.assertEqual(value, stored[key])

    def test_concurrent_edit_is_skipped(self):
        self.assert_concurrent_change_skipped(
            {
                "_etag": "edited",
                "_current_version": 8,
                "_updated": self.now,
                "expiry": self.now + timedelta(days=30),
            }
        )

    def test_concurrent_desk_move_is_skipped_with_etag_change(self):
        self.assert_concurrent_change_skipped({"task": {"desk": ObjectId(), "stage": ObjectId()}, "_etag": "moved"})

    def test_concurrent_stage_move_is_skipped_with_etag_change(self):
        self.assert_concurrent_change_skipped({"task": {"desk": self.desk_id, "stage": ObjectId()}, "_etag": "moved"})

    def test_concurrent_publish_is_skipped_with_etag_change(self):
        self.assert_concurrent_change_skipped({"state": CONTENT_STATE.PUBLISHED, "_etag": "published"})

    def test_concurrent_expiry_change_is_skipped_with_etag_change(self):
        self.assert_concurrent_change_skipped({"expiry": self.now + timedelta(days=30), "_etag": "edited"})

    def test_concurrent_version_change_is_skipped_with_etag_change(self):
        self.assert_concurrent_change_skipped({"_current_version": 8, "_etag": "edited"})

    def test_concurrent_etag_change_is_skipped_without_version_change(self):
        self.assert_concurrent_change_skipped({"_etag": "edited"})

    def test_concurrent_removal_is_skipped(self):
        self.assert_concurrent_change_skipped(remove=True)

    def test_atomic_write_uses_backend_etag_check_and_sets_expiry_and_timestamp(self):
        item = self.insert_item()
        collection = self.app.data.get_mongo_collection("archive")
        original = collection.find_one({"_id": item["_id"]})
        with patch.object(self.app.data.mongo, "get_collection_with_write_concern", return_value=collection):
            with patch.object(collection, "update_one", wraps=collection.update_one) as update:
                with patch("apps.archive.set_expiry.utcnow", return_value=self.now):
                    self.assertEqual(1, SetExpiry().run("Sports News", days=5))
        expiry = self.now + timedelta(days=5)
        self.assertEqual(
            {"_id": item["_id"], "_etag": item["_etag"]},
            update.call_args.args[0],
        )
        self.assertEqual({"$set": {"expiry": expiry, "_updated": self.now}}, update.call_args.args[1])
        original["expiry"] = expiry
        original["_updated"] = self.now
        self.assertEqual(original, collection.find_one({"_id": item["_id"]}))

    def test_indexing_reads_current_document_after_successful_write(self):
        item = self.insert_item()
        collection = self.app.data.get_mongo_collection("archive")
        update_one = collection.update_one
        changes = {
            "state": CONTENT_STATE.PUBLISHED,
            "_current_version": 8,
            "_etag": "published",
            "_updated": self.now,
            "expiry": self.now + timedelta(days=30),
        }

        def publish_after_write(query, update):
            result = update_one(query, update)
            update_one({"_id": item["_id"]}, {"$set": changes})
            return result

        with patch.object(self.app.data.mongo, "get_collection_with_write_concern", return_value=collection):
            with patch.object(collection, "update_one", side_effect=publish_after_write):
                self.assertEqual(1, SetExpiry().run("Sports News", days=5))
        item.update(changes)
        self.assert_expiry(item, changes["expiry"])

    def test_indexing_failure_is_not_reported_as_success(self):
        self.insert_item()
        with patch.object(self.app.data.elastic, "update", side_effect=RuntimeError("Index failed")):
            with patch("builtins.print") as output:
                with self.assertRaisesRegex(RuntimeError, "Index failed"):
                    SetExpiry().run("Sports News", days=5)
        output.assert_not_called()

    def test_cli_options(self):
        self.assertIsInstance(COMMANDS["archive:set_expiry"], SetExpiry)
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
