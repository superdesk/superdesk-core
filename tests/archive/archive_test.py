# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from bson import ObjectId
from pytz import timezone
from datetime import timedelta, datetime
from copy import deepcopy
from unittest import mock

import superdesk
import superdesk.signals as signals
from superdesk.errors import SuperdeskApiError
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from superdesk.metadata.item import CONTENT_STATE
from apps.archive.archive import update_image_caption, update_associations
from apps.archive.common import (
    validate_schedule,
    format_dateline_to_locmmmddsrc,
    convert_task_attributes_to_objectId,
    get_default_source,
    set_default_source,
    get_dateline_city,
    transtype_metadata,
)
from apps.publish.content import publish
from apps.search_providers import register_search_provider, registered_search_providers


NOW = utcnow()


class ArchiveTestCase(TestCase):
    def setUp(self):
        super().setUp()
        search_provider = {"_id": 1, "source": "ABC", "name": "ABC", "search_provider": "ABC"}
        self.app.data.insert("search_providers", [search_provider])
        if not registered_search_providers.get("ABC"):
            register_search_provider("ABC", fetch_endpoint="ABC", label="ABC")

    def test_validate_schedule(self):
        validate_schedule(utcnow() + timedelta(hours=2))

    def test_validate_schedule_at_utc_zero_hours(self):
        validate_schedule((utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))

    def test_validate_schedule_date_with_datetime_as_string_raises_superdeskApiError(self):
        self.assertRaises(SuperdeskApiError, validate_schedule, "2015-04-27T10:53:48+00:00")

    def test_validate_schedule_date_with_datetime_in_past_raises_superdeskApiError(self):
        self.assertRaises(SuperdeskApiError, validate_schedule, utcnow() + timedelta(hours=-2))

    def _get_located_and_current_utc_ts(self):
        current_ts = utcnow()
        located = {
            "dateline": "city",
            "city_code": "Sydney",
            "state": "NSW",
            "city": "Sydney",
            "state_code": "NSW",
            "country_code": "AU",
            "tz": "Australia/Sydney",
            "country": "Australia",
        }

        current_timestamp = datetime.fromtimestamp(current_ts.timestamp(), tz=timezone(located["tz"]))
        if current_timestamp.month == 9:
            formatted_date = "Sept {}".format(current_timestamp.strftime("%-d"))
        elif 3 <= current_timestamp.month <= 7:
            formatted_date = current_timestamp.strftime("%B %-d")
        else:
            formatted_date = current_timestamp.strftime("%b %-d")

        return located, formatted_date, current_ts

    def test_format_dateline_to_format_when_only_city_is_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, "SYDNEY, %s %s -" % (formatted_date, get_default_source()))

    def test_format_dateline_to_format_when_only_city_and_state_are_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()

        located["dateline"] = "city,state"
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, "SYDNEY, NSW, %s %s -" % (formatted_date, get_default_source()))

    def test_format_dateline_to_format_when_only_city_and_country_are_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()

        located["dateline"] = "city,country"
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, "SYDNEY, AU, %s %s -" % (formatted_date, get_default_source()))

    def test_format_dateline_to_format_when_city_state_and_country_are_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()

        located["dateline"] = "city,state,country"
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, "SYDNEY, NSW, AU, %s %s -" % (formatted_date, get_default_source()))

    def test_if_task_attributes_converted_to_objectid(self):
        doc = {
            "task": {
                "user": "562435231d41c835d7b5fb55",
                "desk": ObjectId("562435241d41c835d7b5fb5d"),
                "stage": "test",
                "last_authoring_desk": 3245,
                "last_production_desk": None,
            }
        }

        convert_task_attributes_to_objectId(doc)
        self.assertIsInstance(doc["task"]["user"], ObjectId)
        self.assertEqual(doc["task"]["desk"], ObjectId("562435241d41c835d7b5fb5d"))
        self.assertEqual(doc["task"]["stage"], "test")
        self.assertEqual(doc["task"]["last_authoring_desk"], 3245)
        self.assertIsNone(doc["task"]["last_production_desk"])

    def test_if_metadata_are_transtyped(self):
        """Check that date metadata in extra are transtyped correctly"""
        content_type = {
            "_id": "type_1",
            "label": "test_type",
            "editor": {"test_date_field": {"order": 1, "section": "header"}},
            "schema": {
                "test_date_field": {
                    "type": "date",
                    "required": False,
                    "enabled": True,
                    "nullable": True,
                }
            },
        }
        self.app.data.insert("content_types", [content_type])
        doc = {
            "_id": "transtype_1",
            "profile": "type_1",
            "extra": {"test_date_field": "2019-11-06T00:00:00+0000"},
        }

        transtype_metadata(doc)
        self.assertIsInstance(doc["extra"]["test_date_field"], datetime)

    def test_if_no_source_defined_on_desk(self):
        desk = {"name": "sports"}
        self.app.data.insert("desks", [desk])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            "_id": "123",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
            "dateline": {"located": located, "date": current_ts},
        }

        set_default_source(doc)
        self.assertEqual(doc["source"], get_default_source())
        self.assertEqual(doc["dateline"]["source"], get_default_source())
        self.assertEqual(doc["dateline"]["text"], "SYDNEY, %s %s -" % (formatted_date, get_default_source()))

    def test_if_source_defined_on_desk(self):
        source = "FOO"
        desk = {"name": "sports", "source": source}
        self.app.data.insert("desks", [desk])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            "_id": "123",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
            "dateline": {"located": located, "date": current_ts},
        }

        set_default_source(doc)
        self.assertEqual(doc["source"], source)
        self.assertEqual(doc["dateline"]["source"], source)
        self.assertEqual(doc["dateline"]["text"], "SYDNEY, %s %s -" % (formatted_date, source))

    def test_if_ingest_provider_source_is_preserved(self):
        desk = {"name": "sports", "source": "FOO"}
        self.app.data.insert("desks", [desk])
        ingest_provider = {"_id": 1, "source": "ABC"}
        self.app.data.insert("ingest_providers", [ingest_provider])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            "_id": "123",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
            "dateline": {"located": located, "date": current_ts},
            "ingest_provider": 1,
        }

        set_default_source(doc)
        self.assertEqual(doc["source"], "ABC")
        self.assertEqual(doc["dateline"]["source"], "ABC")
        self.assertEqual(doc["dateline"]["text"], "SYDNEY, %s %s -" % (formatted_date, "ABC"))

    def test_if_ingest_provider_source_is_not_preserved_for_default_ingest(self):
        desk = {"name": "sports", "source": "FOO"}
        self.app.data.insert("desks", [desk])
        ingest_provider = {"_id": 1, "source": "AAP"}
        self.app.data.insert("ingest_providers", [ingest_provider])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            "_id": "123",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
            "dateline": {"located": located, "date": current_ts},
            "ingest_provider": 1,
        }

        set_default_source(doc)
        self.assertEqual(doc["source"], "FOO")
        self.assertEqual(doc["dateline"]["source"], "FOO")
        self.assertEqual(doc["dateline"]["text"], "SYDNEY, %s %s -" % (formatted_date, "FOO"))

    def test_if_search_provider_source_is_preserved(self):
        desk = {"name": "sports", "source": "FOO"}
        self.app.data.insert("desks", [desk])
        doc = {
            "_id": "123",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
            "type": "picture",
            "ingest_provider": 1,
        }

        set_default_source(doc)
        self.assertEqual(doc["source"], "ABC")

    def test_if_item_has_source_then_search_provider_source_is_not_used(self):
        desk = {"name": "sports", "source": "FOO"}
        self.app.data.insert("desks", [desk])
        doc = {
            "_id": "123",
            "task": {"desk": desk["_id"], "stage": desk["working_stage"]},
            "type": "picture",
            "ingest_provider": 1,
            "source": "bar",
        }

        set_default_source(doc)
        self.assertEqual(doc["source"], "bar")

    def test_if_image_caption_is_updated(self):
        body = """
        "body_html" : "<p>test 33</p>\n<!-- EMBED START Image {id: \"embedded9127149191\"} -->\n
        <figure><img src=\"http://localhost:5000/api/upload/58ff025eb611402decdb82e1/raw?_schema=http\" alt=\"aa\" />
        <figcaption>[--description--]</figcaption></figure>\n
        <!-- EMBED END Image {id: \"embedded9127149191\"} -->\n<p>faffaf</p>
        """
        changed_body = """
        "body_html" : "<p>test 33</p>\n<!-- EMBED START Image {id: \"embedded9127149191\"} -->\n
        <figure><img src=\"http://localhost:5000/api/upload/58ff025eb611402decdb82e1/raw?_schema=http\" alt=\"aa\" />
        <figcaption>new caption</figcaption></figure>\n
        <!-- EMBED END Image {id: \"embedded9127149191\"} -->\n<p>faffaf</p>
        """
        body = update_image_caption(body, "embedded9127149191", "new caption")
        self.assertEqual(body, changed_body)

    def test_update_associations(self):
        doc = {
            "fields_meta": {
                "body_html": {
                    "draftjsState": [
                        {
                            "entityMap": {
                                "1": {
                                    "mutability": "MUTABLE",
                                    "type": "MEDIA",
                                    "data": {"media": {"guid": "guid1", "type": "picture", "alt_text": "media 1"}},
                                },
                                "0": {
                                    "mutability": "MUTABLE",
                                    "type": "MEDIA",
                                    "data": {"media": {"guid": "guid0", "type": "picture", "alt_text": "media 0"}},
                                },
                                "2": {
                                    "mutability": "MUTABLE",
                                    "type": "MEDIA",
                                    "data": {"media": {"guid": "guid2", "type": "picture", "alt_text": "media 2"}},
                                },
                            }
                        }
                    ]
                }
            },
            "associations": {
                "editor_1": {"guid": "guid10", "type": "picture10", "alt_text": "media 10"},
                "editor_7": {"guid": "guid7", "type": "picture7", "alt_text": "media 7"},
                "featuremedia": {"guid": "guid11", "type": "picture11"},
            },
        }

        update_associations(doc)

        self.assertEqual(len(doc["associations"]), 5)
        self.assertEqual(doc["associations"]["editor_0"], {"guid": "guid0", "type": "picture", "alt_text": "media 0"})
        self.assertEqual(doc["associations"]["editor_1"], {"guid": "guid1", "type": "picture", "alt_text": "media 1"})
        self.assertEqual(doc["associations"]["editor_2"], {"guid": "guid2", "type": "picture", "alt_text": "media 2"})
        self.assertEqual(doc["associations"]["editor_7"], None)
        self.assertEqual(doc["associations"]["featuremedia"], {"guid": "guid11", "type": "picture11"})

    def test_get_dateline_city_None(self):
        self.assertEqual(get_dateline_city(None), "")

    def test_get_dateline_city_located_as_none(self):
        self.assertEqual(get_dateline_city({"located": None}), "")

    def test_get_dateline_city_located_as_none_text_as_none(self):
        self.assertEqual(get_dateline_city({"located": None, "text": None}), "")

    def test_get_dateline_city_from_text(self):
        self.assertEqual(get_dateline_city({"located": None, "text": "Sydney, 9 July AAP"}), "Sydney")

    def test_get_dateline_city_from_located(self):
        self.assertEqual(
            get_dateline_city({"located": {"city": "Melbourne"}, "text": "Sydney, 9 July AAP"}), "Melbourne"
        )

    def test_get_dateline_city_from_text_no_city(self):
        self.assertEqual(get_dateline_city({"located": {"city": None}, "text": "Sydney, 9 July AAP"}), "Sydney")

    def test_get_dateline_city_from_located_with_country(self):
        self.assertEqual(get_dateline_city({"located": {"country": "Canada"}, "text": "Sydney, 9 July AAP"}), "Sydney")

    def test_get_dateline_city_from_text_with_city_state(self):
        self.assertEqual(get_dateline_city({"located": None, "text": "City, State, 9 July AAP"}), "City, State")

    def test_firstpublished(self):
        """Check that "firstpublihed" field is set correctly

        the test create a story, check firstpublished field, then correct it
        and check again that correction is done and firstpublished has not changed
        """
        archive_service = superdesk.get_resource_service("archive")
        correct_service = superdesk.get_resource_service("archive_correct")
        publish_service = superdesk.get_resource_service("archive_publish")
        item = {
            "_id": "foo",
            "guid": "foo",
            "unique_name": "foo",
            "type": "text",
            "state": CONTENT_STATE.SUBMITTED,
            "_current_version": 1,
            "rewrite_of": "bar",
        }
        archive_service.create([item])
        with mock.patch.object(publish, "utcnow", lambda: NOW):
            publish_service.patch("foo", {"body_html": "original"})
        created = publish_service.find_one(None, _id="foo")
        self.assertEqual(NOW, created["firstpublished"])
        correct_service.patch("foo", {"body_html": "corrected"})
        # we try to update to check that "firstpublished" is not modified
        # note that utcnow MUST NOT be mocked here, else the test would be pointless
        corrected = publish_service.find_one(None, _id="foo")
        self.assertEqual("corrected", corrected["body_html"])
        self.assertEqual(NOW, corrected["firstpublished"])

    def test_update_signals(self):
        def handler(sender, **kwargs):
            pass

        item_update_mock = mock.create_autospec(handler)
        item_updated_mock = mock.create_autospec(handler)

        signals.item_update.connect(item_update_mock)
        signals.item_updated.connect(item_updated_mock)

        archive_service = superdesk.get_resource_service("archive")
        item = {"_id": "foo"}
        ids = archive_service.create([item])

        updates = {"foo": "bar"}
        archive_service.update(ids[0], updates, item)

        updated = item.copy()
        updated.update(updates)
        item_update_mock.assert_called_once_with(archive_service, updates=updates, original=item)
        item_updated_mock.assert_called_once_with(archive_service, item=updated, original=item)

        signals.item_update.disconnect(item_update_mock)
        signals.item_updated.disconnect(item_updated_mock)

    def test_duplicate_signals(self):
        def handler(sender, item, original, operation):
            pass

        duplicate_handler_mock = mock.create_autospec(handler)
        duplicated_handler_mock = mock.create_autospec(handler)

        signals.item_duplicate.connect(duplicate_handler_mock)
        signals.item_duplicated.connect(duplicated_handler_mock)

        archive_service = superdesk.get_resource_service("archive")
        original_item = {
            "_id": "original",
            "headline": "original item",
            "language": "en",
        }
        archive_service.create([original_item])
        original_item = archive_service.find_one(None, _id="original")
        item = deepcopy(original_item)
        item["language"] = "fr"
        translate_guid = archive_service.duplicate_item(item, operation="translate")

        # `assert_called_once_with` is not used due to a lot of metadata is generated during duplication
        assert duplicate_handler_mock.call_count == 1  # use `assert_called_once` for python>=3.6
        assert duplicate_handler_mock.call_args[0][0] is archive_service
        assert duplicate_handler_mock.call_args[1]["item"]["guid"] == translate_guid
        assert duplicate_handler_mock.call_args[1]["original"]["_id"] == original_item["_id"]
        assert duplicate_handler_mock.call_args[1]["operation"] == "translate"

        assert duplicated_handler_mock.call_count == 1
        assert duplicated_handler_mock.call_args[0][0] is archive_service
        assert duplicated_handler_mock.call_args[1]["item"]["guid"] == translate_guid
        assert duplicated_handler_mock.call_args[1]["original"]["_id"] == original_item["_id"]
        assert duplicated_handler_mock.call_args[1]["operation"] == "translate"

        signals.item_duplicate.disconnect(duplicate_handler_mock)
        signals.item_duplicated.disconnect(duplicated_handler_mock)
