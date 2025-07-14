from datetime import datetime, timedelta, timezone
from bson import ObjectId
from unittest.mock import patch

from superdesk.tests import TestCase
from superdesk.publish.subscribers_schedule import update_subscriber_activation_states


class SubscriberScheduleTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2025, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

        # Patch utcnow
        patcher = patch("superdesk.publish.subscribers_schedule.utcnow")
        self.mock_utcnow = patcher.start()
        self.mock_utcnow.return_value = self.now
        self.addCleanup(patcher.stop)

    def insert_subscriber(self, name, start_offset_days, end_offset_days, is_active):
        """Utility to insert subscriber with schedule offset from self.now"""
        start = self.now + timedelta(days=start_offset_days)
        end = self.now + timedelta(days=end_offset_days)

        return self.app.data.insert("subscribers", [
            {
                "_id": ObjectId(),
                "name": name,
                "is_active": is_active,
                "schedule": {
                    "startDate": start,
                    "endDate": end,
                }
            }
        ])[0]

    def test_activation_and_deactivation_logic(self):
        # Subscriber to activate (inactive but in schedule)
        s1 = self.insert_subscriber("activate_me", -1, 1, False)
        # Subscriber to deactivate (active but expired)
        s2 = self.insert_subscriber("deactivate_me", -10, -1, True)
        # Subscriber before schedule (should be deactivated)
        s3 = self.insert_subscriber("too_early", 1, 10, True)
        # Subscriber already active and in schedule
        s4 = self.insert_subscriber("already_active", -1, 1, True)

        update_subscriber_activation_states()

        updated_s1 = self.app.data.find_one("subscribers", req=None, _id=s1)
        updated_s2 = self.app.data.find_one("subscribers", req=None, _id=s2)
        updated_s3 = self.app.data.find_one("subscribers", req=None, _id=s3)
        updated_s4 = self.app.data.find_one("subscribers", req=None, _id=s4)

        self.assertTrue(updated_s1["is_active"], "s1 should have been activated")
        self.assertFalse(updated_s2["is_active"], "s2 should have been deactivated")
        self.assertFalse(updated_s3["is_active"], "s3 should have been deactivated")
        self.assertTrue(updated_s4["is_active"], "s4 should remain active (no change)")
