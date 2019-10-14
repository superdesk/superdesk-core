import pytz
import warnings

from datetime import datetime
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

    def test_add_timestamps_warning(self):
        item = {}
        feeding_service = TestFeedingService()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            feeding_service.add_timestamps(item)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)

    def test_localize_timestamps(self):
        item = {'firstcreated': datetime(2019, 10, 15, 10, 59, 0)}
        self.assertIsNone(item['firstcreated'].tzinfo)
        feeding_service = TestFeedingService()
        feeding_service.localize_timestamps(item)
        self.assertEqual(pytz.utc, item['firstcreated'].tzinfo)
