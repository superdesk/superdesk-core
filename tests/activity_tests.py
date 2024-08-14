# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.activity import ActivityService, get_recipients
from superdesk.publish import init_app
from superdesk.tests import TestCase
from superdesk.types import User


class ActivityTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
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

    def test_get_recipients_filters_out_users_not_activated(self):
        users = [
            User(
                {
                    "username": "test1",
                    "email": "test_1@test.com",
                    "needs_activation": False,
                    "is_enabled": True,
                    "is_active": True,
                    "user_preferences": {"email:notification": {"enabled": True}},
                }
            ),
            User(
                {
                    "username": "test2",
                    "email": "test_2@test.com",
                    "needs_activation": True,
                    "is_enabled": True,
                    "is_active": True,
                    "user_preferences": {"email:notification": {"enabled": True}},
                }
            ),
        ]

        recipients = get_recipients(user_list=users)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0], "test_1@test.com")

    def test_get_recipients_filters_out_users_with_disabled_notification(self):
        users = [
            User(
                {
                    "username": "test1",
                    "email": "test_1@test.com",
                    "needs_activation": False,
                    "is_enabled": True,
                    "is_active": True,
                    "user_preferences": {"email:notification": {"enabled": False}},
                }
            ),
        ]

        recipients = get_recipients(user_list=users, notification_name="test")
        assert len(recipients) == 0

        users[0]["user_preferences"]["email:notification"]["enabled"] = True
        recipients = get_recipients(user_list=users, notification_name="test")
        assert len(recipients) == 1
