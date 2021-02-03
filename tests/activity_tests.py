# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from unittest import mock

from superdesk.activity import ActivityService, ACTIVITY_ERROR, get_recipients
from superdesk.publish import init_app
from superdesk.tests import TestCase


def mock_get_resource_service(resource_name):
    return MockPreferenceService()


class MockPreferenceService:
    def email_notification_is_enabled(self, preferences=None):
        send_email = preferences.get("email:notification", {}) if isinstance(preferences, dict) else {}

        return send_email and send_email.get("enabled", False)


class ActivityTestCase(TestCase):
    def setUp(self):
        init_app(self.app)

    def test_if_user_is_in_recipients(self):
        activity = {"recipients": [{"user_id": "1", "read": True}, {"user_id": "2", "read": False}]}

        self.assertTrue(ActivityService().is_recipient(activity, "1"))
        self.assertTrue(ActivityService().is_recipient(activity, "2"))
        self.assertFalse(ActivityService().is_recipient(activity, "3"))

    def test_is_read(self):
        activity = {"recipients": [{"user_id": "1", "read": True}, {"user_id": "2", "read": False}]}

        self.assertTrue(ActivityService().is_read(activity, "1"))
        self.assertFalse(ActivityService().is_read(activity, "2"))
        self.assertFalse(ActivityService().is_read(activity, "3"))

    @mock.patch("superdesk.activity.get_resource_service", mock_get_resource_service)
    def test_get_recipients_filters_out_users_not_activated(self):
        users = [
            {
                "email": "test_1@test.com",
                "needs_activation": False,
                "is_enabled": True,
                "is_active": True,
                "user_preferences": {"email:notification": {"enabled": True}},
            },
            {
                "email": "test_2@test.com",
                "needs_activation": True,
                "is_enabled": True,
                "is_active": True,
                "user_preferences": {"email:notification": {"enabled": True}},
            },
        ]

        recipients = get_recipients(user_list=users, activity_name=ACTIVITY_ERROR)
        self.assertEqual(len(recipients), 1)
