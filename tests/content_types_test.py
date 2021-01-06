import copy
import bson

from unittest import mock
from datetime import timedelta
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.content_types import apply_schema

import apps.content_types.content_types as content_types


class MockService:
    def find_one(self, req, **lookup):
        return {"schema": {"headline": {}}}


class MockVocabulariesService:
    def get_forbiden_custom_vocabularies(self):
        return [
            {
                "_id": "test",
                "field_type": None,
                "selection_type": "do not show",
                "display_name": "test",
                "helper_text": "test",
                "unique_field": "qcode",
            }
        ]


class ContentTypesTestCase(TestCase):
    def test_apply_schema_default(self):
        item = {"guid": "guid", "headline": "foo"}
        self.assertEqual(item, apply_schema(item))

    @mock.patch("apps.content_types.content_types.get_resource_service", return_value=MockService())
    def test_apply_schema_profile(self, mock):
        item = {"headline": "foo", "slugline": "bar", "guid": "1", "profile": "test"}
        self.assertEqual({"headline": "foo", "guid": "1", "profile": "test"}, apply_schema(item))

    @mock.patch.object(content_types, "get_fields_map_and_names", lambda: ({}, {}))
    def test_minlength(self):
        """Check that minlength is not modified when it is set

        check is done with required set
        """
        original = {
            "schema": {
                "body_html": {"required": True, "enabled": True},
            }
        }
        updates = copy.deepcopy(original)
        updates["schema"]["body_html"]["minlength"] = "99"
        content_types.ContentTypesService().on_update(updates, original)
        self.assertEqual(updates["schema"]["body_html"]["minlength"], "99")

    def test_get_output_name(self):
        _id = bson.ObjectId()
        service = content_types.ContentTypesService()
        with mock.patch.object(service, "find_one", return_value={"label": "Test Label 123 *#$"}):
            self.assertEqual("TestLabel123", service.get_output_name(_id))

    @mock.patch("apps.content_types.content_types.get_resource_service", return_value=MockVocabulariesService())
    def test_clean_doc(self, mock):
        profile = {
            "schema": {"test": {"type": "list", "required": False, "default": []}},
            "editor": {"test": {"enabled": False, "field_name": "test"}},
        }

        content_types.clean_doc(profile)
        self.assertEqual({"schema": {}, "editor": {}}, profile)

    # Do not remove or modify the following line, the test would always pass without
    # the dict with "hashtags" returned by "get_fields_map_and_names"
    @mock.patch.object(content_types, "get_fields_map_and_names", lambda: ({"hashtags": "hashtags"}, {}))
    def test_subject(self):
        """Check that subject is not set if it's not present in editor (SDESK-3745)

        If we had custom vocabularies in schema, subject was added to "schema" even if not
        present if "editor", resulting in validation error.
        """
        original = {
            "_id": "5b1a4774b10de731297716ad",
            "editor": {
                "hashtags": {"order": 5, "enabled": True, "field_name": "Hashtags"},
                "subject": {"order": 1, "sdWidth": "full", "required": True, "enabled": True},
            },
            "schema": {
                "subject": {
                    "mandatory_in_list": {"scheme": {}},
                    "schema": {},
                    "type": "list",
                    "required": True,
                    "default": [],
                    "nullable": False,
                },
                "hashtags": {"type": "list", "required": False, "default": []},
            },
        }

        updates = copy.deepcopy(original)
        # the updates are only removing the "subject" field
        updates["schema"]["subject"] = updates["editor"]["subject"] = None
        content_types.ContentTypesService().on_update(updates, original)
        self.assertFalse(updates["schema"]["subject"]["required"])

    def test_prepare_for_edit_updated_now(self):
        doc = {
            "editor": {},
            "schema": {},
            "_updated": utcnow() - timedelta(days=5),
        }

        content_types.prepare_for_edit_content_type(doc)
        self.assertGreaterEqual(doc["_updated"], utcnow() - timedelta(seconds=2))
