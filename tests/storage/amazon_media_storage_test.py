
import time
from superdesk.tests import TestCase
from superdesk.storage.amazon.amazon_media_storage import AmazonMediaStorage


class AmazonMediaStorageTestCase(TestCase):

    def test_url_for_media(self):
        # create a dummy app containing only the settings
        media_id = '123'
        time_id = time.strftime('%Y%m%d')
        # set s3 settings and test the output
        self.app.config['AMAZON_CONTAINER_NAME'] = 'AMAZON_CONTAINER_NAME'
        self.app.config['AMAZON_S3_USE_HTTPS'] = True
        self.app.config['AMAZON_SERVE_DIRECT_LINKS'] = True
        self.assertEqual(AmazonMediaStorage(self.app).url_for_media(media_id),
                         'https://AMAZON_CONTAINER_NAME.s3-us-east-1.amazonaws.com/%s/%s' % (time_id, media_id))
        self.app.config['AMAZON_S3_USE_HTTPS'] = False
        self.assertEqual(AmazonMediaStorage(self.app).url_for_media(media_id),
                         'http://AMAZON_CONTAINER_NAME.s3-us-east-1.amazonaws.com/%s/%s' % (time_id, media_id))
        self.app.config['AMAZON_REGION'] = 'eu-west-1'
        self.assertEqual(AmazonMediaStorage(self.app).url_for_media(media_id),
                         'http://AMAZON_CONTAINER_NAME.s3-eu-west-1.amazonaws.com/%s/%s' % (time_id, media_id))
