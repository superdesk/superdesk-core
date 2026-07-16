# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from superdesk.macros.set_default_template_metadata import set_default_template_metadata


class SetDefaultTemplateMetadataTestCase(TestCase):
    """Tests for the 'Set default template metadata' core macro.

    These tests verify that the macro correctly fills empty metadata fields
    from the desk's default content template, while ensuring that
    ``fields_meta`` (a client-side DraftJS editor state) is never copied
    from the template into the item — which would cause the editor to
    display an empty body even when ``body_html`` has content.
    """

    DESK_ID = "test-desk-1"
    TEMPLATE_ID = "test-template-1"

    EMPTY_DRAFTJS_STATE = {
        "blocks": [
            {
                "key": "test1",
                "text": "",
                "type": "unstyled",
                "depth": 0,
                "inlineStyleRanges": [],
                "entityRanges": [],
            }
        ],
        "entityMap": {},
    }

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.data.insert(
            "desks",
            [
                {
                    "_id": self.DESK_ID,
                    "name": "Test Desk",
                    "default_content_template": self.TEMPLATE_ID,
                }
            ],
        )
        self.app.data.insert(
            "content_templates",
            [
                {
                    "_id": self.TEMPLATE_ID,
                    "template_name": "test template",
                    "template_type": "create",
                    "data": {
                        "headline": "",
                        "body_html": "",
                        "urgency": 3,
                        "slugline": "Default slugline",
                        "fields_meta": {
                            "headline": {"draftjsState": [self.EMPTY_DRAFTJS_STATE]},
                            "body_html": {"draftjsState": [self.EMPTY_DRAFTJS_STATE]},
                        },
                    },
                }
            ],
        )
        self.app.data.insert(
            "vocabularies",
            [
                {"_id": "categories", "items": [{"is_active": True, "name": "General", "qcode": "a"}]},
            ],
        )

    def _create_ingested_item(self):
        return {
            "_id": "test-item-1",
            "type": "text",
            "headline": "Original headline from ingest",
            "body_html": "<p>Original body content from ingest</p>",
        }

    async def test_fields_meta_not_copied(self):
        """Ensure fields_meta is never copied from the template into the item."""
        item = self._create_ingested_item()
        result = set_default_template_metadata(item, dest_desk_id=self.DESK_ID)
        self.assertIsNotNone(result, "Macro should return the item")
        self.assertNotIn(
            "fields_meta",
            result,
            "fields_meta must not be copied from the template into the item",
        )

    async def test_metadata_fields_copied(self):
        """Ensure empty metadata fields are filled from the template."""
        item = self._create_ingested_item()
        # Remove urgency so it can be filled from the template
        item.pop("urgency", None)
        result = set_default_template_metadata(item, dest_desk_id=self.DESK_ID)
        self.assertIsNotNone(result, "Macro should return the item")
        self.assertEqual(result.get("urgency"), 3, "urgency should be filled from the template")
        self.assertEqual(result.get("slugline"), "Default slugline", "slugline should be filled from the template")

    async def test_existing_fields_not_overwritten(self):
        """Ensure fields already present in the item are not overwritten by empty template values."""
        item = self._create_ingested_item()
        result = set_default_template_metadata(item, dest_desk_id=self.DESK_ID)
        self.assertIsNotNone(result, "Macro should return the item")
        self.assertEqual(
            result.get("headline"),
            "Original headline from ingest",
            "headline should not be overwritten by the template's empty headline",
        )
        self.assertEqual(
            result.get("body_html"),
            "<p>Original body content from ingest</p>",
            "body_html should not be overwritten by the template's empty body_html",
        )

    async def test_fields_meta_not_copied_when_item_has_no_fields_meta(self):
        """Ensure the macro doesn't introduce fields_meta on ingested items (the STT-17421 scenario)."""
        item = self._create_ingested_item()
        # Ingested items have no fields_meta at all
        self.assertNotIn("fields_meta", item)
        result = set_default_template_metadata(item, dest_desk_id=self.DESK_ID)
        self.assertIsNotNone(result, "Macro should return the item")
        self.assertNotIn(
            "fields_meta",
            result,
            "fields_meta must not be introduced on ingested items by the macro",
        )
