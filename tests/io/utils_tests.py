# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime, timedelta

from superdesk.tests import TestCase
from superdesk.io.commands.update_ingest import is_new_version


class UtilsTestCase(TestCase):
    def test_is_new_version(self):
        self.assertTrue(is_new_version({"version": 2}, {"version": 1}))
        self.assertTrue(
            is_new_version({"versiocreated": datetime.now()}, {"versioncreated": datetime.now() - timedelta(days=1)})
        )
        self.assertTrue(is_new_version({"version": "10"}, {"version": "2"}))

        self.assertFalse(is_new_version({"version": 1}, {"version": 1}))
        self.assertFalse(is_new_version({"version": "123"}, {"version": "123"}))
        self.assertFalse(is_new_version({"versioncreated": datetime.now()}, {"versioncreated": datetime.now()}))

    def test_is_new_version_content(self):
        self.assertTrue(is_new_version({"headline": "foo"}, {}))
        self.assertTrue(is_new_version({"headline": "foo"}, {"headline": "bar"}))
        self.assertTrue(
            is_new_version(
                {"renditions": {"original": {"href": "foo"}}},
                {"renditions": {"original": {"href": "bar"}}},
            )
        )
        self.assertTrue(
            is_new_version(
                {"subject": [{"name": "foo", "qcode": "foo"}]},
                {"subject": [{"name": "bar", "qcode": "bar"}]},
            )
        )

        self.assertFalse(is_new_version({}, {}))
        self.assertFalse(is_new_version({"headline": "foo"}, {"headline": "foo", "source": "test"}))
        self.assertFalse(
            is_new_version(
                {"renditions": {"original": {"href": "foo"}}},
                {"renditions": {"original": {"href": "foo"}}},
            )
        )
        self.assertFalse(
            is_new_version(
                {"subject": [{"name": "foo", "qcode": "foo"}]},
                {"subject": [{"name": "foo", "qcode": "foo"}]},
            )
        )

    def test_is_new_version_ignores_expiry(self):
        yesterday = datetime.now() - timedelta(days=1)
        self.assertFalse(
            is_new_version(
                {"headline": "foo", "firstcreated": None, "expiry": datetime.now()},
                {"headline": "foo", "firstcreated": yesterday, "expiry": yesterday},
            )
        )
