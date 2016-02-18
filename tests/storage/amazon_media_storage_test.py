
import time
from superdesk.tests import TestCase
from superdesk.storage.amazon.amazon_media_storage import AmazonMediaStorage


class AmazonMediaStorageTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.app.config['AMAZON_CONTAINER_NAME'] = 'AMAZON_CONTAINER_NAME'
        self.app.config['AMAZON_S3_USE_HTTPS'] = True
        self.app.config['AMAZON_SERVE_DIRECT_LINKS'] = True
        self.app.config['AMAZON_SERVER'] = 'amazonaws.com'
        self.amazon = AmazonMediaStorage(self.app)

    def test_media_id(self):
        filename = 'test'
        time_id = time.strftime('%Y%m%d')
        media_id = self.amazon.media_id(filename)
        self.assertEqual('%s/%s' % (time_id, filename), media_id)

    def test_url_for_media(self):
        media_id = 'test'
        self.assertEqual(self.amazon.url_for_media(media_id),
                         'https://AMAZON_CONTAINER_NAME.s3-us-east-1.amazonaws.com/%s' % (media_id))
        self.app.config['AMAZON_S3_USE_HTTPS'] = False
        self.assertEqual(self.amazon.url_for_media(media_id),
                         'http://AMAZON_CONTAINER_NAME.s3-us-east-1.amazonaws.com/%s' % (media_id))
        self.app.config['AMAZON_REGION'] = 'eu-west-1'
        self.assertEqual(self.amazon.url_for_media(media_id),
                         'http://AMAZON_CONTAINER_NAME.s3-eu-west-1.amazonaws.com/%s' % (media_id))
