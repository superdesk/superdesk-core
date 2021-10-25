# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from nose.tools import assert_raises

from apps.archive.common import get_item_expiry
from apps.tasks import (
    apply_stage_rule,
    apply_onstage_rule,
    compare_dictionaries,
    MACRO_INCOMING,
    MACRO_OUTGOING,
    MACRO_ONSTAGE,
)
from superdesk.errors import SuperdeskApiError
from superdesk.utc import get_expiry_date
from superdesk.tests import TestCase


class TasksTestCase(TestCase):
    def test_get_global_content_expiry(self):
        calculated_minutes = get_item_expiry(desk=None, stage=None)
        reference_minutes = get_expiry_date(self.ctx.app.config["CONTENT_EXPIRY_MINUTES"])
        self.assertEquals(calculated_minutes.hour, reference_minutes.hour)
        self.assertEquals(calculated_minutes.minute, reference_minutes.minute)

    def test_get_desk_content_expiry(self):
        desk = {"content_expiry": 10}
        calculated_minutes = get_item_expiry(desk=desk, stage=None)
        reference_minutes = get_expiry_date(10)
        self.assertEquals(calculated_minutes.hour, reference_minutes.hour)
        self.assertEquals(calculated_minutes.minute, reference_minutes.minute)

    def test_get_stage_content_expiry(self):
        stage = {"content_expiry": 10}
        calculated_minutes = get_item_expiry(desk=None, stage=stage)
        reference_minutes = get_expiry_date(10)
        self.assertEquals(calculated_minutes.hour, reference_minutes.hour)
        self.assertEquals(calculated_minutes.minute, reference_minutes.minute)

    def test_apply_incoming_stage_rule(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"anpa_take_key": "x"}
        stage = {"incoming_macro": "populate_abstract"}
        with self.app.app_context():
            apply_stage_rule(doc, update, stage, MACRO_INCOMING)
            self.assertEquals(update["abstract"], "Test-1")

    def test_apply_outgoing_stage_rule(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"anpa_take_key": "x"}
        stage = {"outgoing_macro": "populate_abstract"}
        with self.app.app_context():
            apply_stage_rule(doc, update, stage, MACRO_OUTGOING)
            self.assertEquals(update["abstract"], "Test-1")

    def test_apply_stage_incoming_validation_rule(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"headline": "x"}
        stage = {"incoming_macro": "take_key_validator"}
        with self.app.app_context():
            with assert_raises(SuperdeskApiError):
                apply_stage_rule(doc, update, stage, MACRO_INCOMING)

    def test_apply_stage_incoming_validation_rule_passes(self):
        doc = {"id": "1", "body_html": "Test-1", "anpa_take_key": "a"}
        update = {"headline": "x"}
        stage = {"incoming_macro": "take_key_validator"}
        with self.app.app_context():
            apply_stage_rule(doc, update, stage, MACRO_INCOMING)

    def test_apply_stage_incoming_validation_rule_ignored(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"headline": "x"}
        stage = {"outgoing_macro": "take_key_validator"}
        with self.app.app_context():
            apply_stage_rule(doc, update, stage, MACRO_INCOMING)

    def test_apply_stage_outgoing_validation_rule_ignored(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"headline": "x"}
        stage = {"incoming_macro": "take_key_validator"}
        with self.app.app_context():
            apply_stage_rule(doc, update, stage, MACRO_OUTGOING)

    def test_apply_stage_outgoing_validation_rule(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"headline": "x"}
        stage = {"outgoing_macro": "take_key_validator"}
        with self.app.app_context():
            with assert_raises(SuperdeskApiError):
                apply_stage_rule(doc, update, stage, MACRO_OUTGOING)

    def test_apply_on_stage_validation_rule(self):
        doc = {"id": "1", "body_html": "Test-1"}
        update = {"headline": "x"}
        stage = {"onstage_macro": "take_key_validator"}
        with self.app.app_context():
            with assert_raises(SuperdeskApiError):
                apply_stage_rule(doc, update, stage, MACRO_ONSTAGE)

    def test_apply_onstage_rule(self):
        doc = {"id": "1", "body_html": "Test-1", "task": {"stage": 1}}
        stages = [{"_id": 1, "onstage_macro": "take_key_validator"}]
        self.app.data.insert("stages", stages)

        with self.app.app_context():
            with assert_raises(SuperdeskApiError):
                apply_onstage_rule(doc, 1)

    def test_apply_onstage_rule_applies(self):
        doc = {"id": "1", "body_html": "Test-1", "task": {"stage": 1}}
        stages = [{"_id": 1, "onstage_macro": "populate_abstract"}]
        self.app.data.insert("stages", stages)

        with self.app.app_context():
            apply_onstage_rule(doc, 1)
            self.assertEquals(doc["abstract"], "Test-1")

    def test_compare_dictionaries(self):
        original = {"id": 1, "body_html": "Test-1"}

        updates = {
            "body_html": "Test-2",
            "headline": "a",
        }

        modified = compare_dictionaries(original, updates)
        self.assertEquals(2, len(modified))
        self.assertTrue("body_html" in modified)
        self.assertTrue("headline" in modified)
