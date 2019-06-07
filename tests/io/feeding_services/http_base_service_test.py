
import unittest

from superdesk.io.feeding_services.http_base_service import HTTPFeedingServiceBase


class FeedingServiceWithUrl(HTTPFeedingServiceBase):

    URL = 'http://example.com'

    fields = []

    def _update():
        pass


class TestFeedingService(unittest.TestCase):

    def test_validate_config_url_null(self):
        service = FeedingServiceWithUrl()
        service.provider = {'config': {'url': None}}
        service.validate_config()
