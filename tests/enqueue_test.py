from unittest.mock import patch
from superdesk.tests import TestCase
from apps.publish.enqueue.enqueue_service import EnqueueService


class NoTakesEnqueueTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.product_ids = self.app.data.insert(
            "products",
            [
                {"name": "all"},
            ],
        )

        self.subscriber_ids = self.app.data.insert(
            "subscribers",
            [
                {"name": "digi", "subscriber_type": "digital", "is_targetable": True, "products": self.product_ids},
            ],
        )

        self.desk_ids = self.app.data.insert(
            "desks",
            [
                {"name": "sports"},
            ],
        )

        self.service = EnqueueService()

    def test_resend_no_takes(self):
        doc = {"_id": "test"}
        subscribers = [s for s in self.app.data.find_all("subscribers")]
        subscriber_codes = self.service._get_subscriber_codes(subscribers)
        with patch.object(self.service, "_resend_to_subscribers") as resend:
            with patch.object(self.service, "publish_content_api") as content_api:
                self.service.resend(doc, subscribers)
                resend.assert_called_with(doc, subscribers, subscriber_codes, {})
                content_api.assert_called_with(doc, [])
