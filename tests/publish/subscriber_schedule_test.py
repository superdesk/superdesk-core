from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch

from superdesk.tests import TestCase
from superdesk.publish.subscribers_schedule import update_subscriber_activation_states


class SubscriberScheduleTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2025, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Patch get_local_today
        patcher = patch("superdesk.publish.subscribers_schedule.get_local_today")
        self.mock_today = patcher.start()
        self.mock_today.return_value = self.now
        self.addCleanup(patcher.stop)

    def insert_subscriber(self, name, start_date, end_date, is_active):
        return self.app.data.insert(
            "subscribers",
            [
                {
                    "_id": ObjectId(),
                    "name": name,
                    "is_active": is_active,
                    "schedule": {
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                }
            ],
        )[0]

    def test_subscriber_activation_and_deactivation_on_exact_date(self):
        today_str = self.now.date().isoformat()

        # Should be activated
        s1 = self.insert_subscriber("should_activate", today_str, "2025-07-20", False)
        # Should be deactivated
        s2 = self.insert_subscriber("should_deactivate", "2025-07-01", today_str, True)
        # Should remain unchanged (not matching today)
        s3 = self.insert_subscriber("unchanged", "2025-07-16", "2025-07-18", False)

        update_subscriber_activation_states()

        updated_s1 = self.app.data.find_one("subscribers", req=None, _id=s1)
        updated_s2 = self.app.data.find_one("subscribers", req=None, _id=s2)
        updated_s3 = self.app.data.find_one("subscribers", req=None, _id=s3)

        self.assertTrue(updated_s1["is_active"], "s1 should have been activated")
        self.assertFalse(updated_s2["is_active"], "s2 should have been deactivated")
        self.assertFalse(updated_s3["is_active"], "s3 should remain unchanged")
