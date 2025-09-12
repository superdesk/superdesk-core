from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import patch

from superdesk.publish_async.resources.subscribers.service import SubscribersService
from superdesk.tests import TestCase
from superdesk.publish_async.resources.subscribers.subscribers_schedule import update_subscriber_activation_states


class SubscriberScheduleTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = SubscribersService()
        self.now = datetime(2025, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Patch get_local_today
        patcher = patch("superdesk.publish_async.resources.subscribers.subscribers_schedule.get_local_today")
        self.mock_today = patcher.start()
        self.mock_today.return_value = self.now
        self.addCleanup(patcher.stop)

    async def insert_subscriber(self, name: str, start_date: str | None, end_date: str | None, is_active: bool):
        subscribers = await self.service.create(
            [
                {
                    "_id": ObjectId(),
                    "name": name,
                    "is_active": is_active,
                    "schedule": {
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                    "email": "test@sourcefabric.org",
                    "subscriber_type": "all",
                    "destinations": [
                        {
                            "name": "test",
                            "format": "json",
                            "delivery_type": "http_push",
                        }
                    ],
                }
            ]
        )
        return subscribers[0].id

    async def test_apply_schedule_status_activation_on_exact_date(self):
        today_str = self.now.date().isoformat()

        # Should be activated
        s1_id = await self.insert_subscriber("should_activate", today_str, "2025-07-20", False)
        # Should be deactivated
        s2_id = await self.insert_subscriber("should_deactivate", "2025-07-01", today_str, True)
        # Should remain unchanged (not matching today)
        s3_id = await self.insert_subscriber("unchanged", "2025-07-16", "2025-07-18", False)

        await update_subscriber_activation_states()

        updated_s1 = await self.service.find_by_id_raw(s1_id)
        updated_s2 = await self.service.find_by_id_raw(s2_id)
        updated_s3 = await self.service.find_by_id_raw(s3_id)

        assert updated_s1
        self.assertTrue(updated_s1["is_active"], "s1 should have been activated")
        assert updated_s2
        self.assertFalse(updated_s2["is_active"], "s2 should have been deactivated")
        assert updated_s3
        self.assertFalse(updated_s3["is_active"], "s3 should remain unchanged")
