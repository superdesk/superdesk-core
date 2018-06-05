from superdesk.tests import TestCase
from superdesk.io.feeding_services import FeedingService
from superdesk.errors import SuperdeskIngestError


class TestFeedingService(FeedingService):
    parser_restricted_values = ['ninjs']

    def _update(self, provider, update):
        pass


class ContentAPITestCase(TestCase):
    def test_publish_to_content_api(self):
        feeding_service = TestFeedingService()

        with self.assertRaises(SuperdeskIngestError):
            feeding_service.config_test({'feed_parser': 'foo'})
