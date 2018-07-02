from unittest.mock import patch
from superdesk.tests import TestCase
from superdesk.io.feeding_services import FeedingService
from superdesk.errors import SuperdeskIngestError


class TestFeedingService(FeedingService):
    Name = 'test_feeding'

    def _update(self, provider, update):
        pass


class FeedingServiceParserTestCase(TestCase):

    def test_restricted_parser(self):
        feeding_service = TestFeedingService()
        with patch.dict('superdesk.io.feeding_services.restricted_feeding_service_parsers',
                        {'test_feeding': {'ninjs': True}}):
            with self.assertRaises(SuperdeskIngestError):
                feeding_service.config_test({'feed_parser': 'foo', 'feeding_service': 'test_feeding'})
