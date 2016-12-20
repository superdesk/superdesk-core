import time
from unittest.mock import patch

from superdesk.tests import TestCase
from superdesk.storage.amazon.amazon_media_storage import AmazonMediaStorage


class AmazonMediaStorageTestCase(TestCase):

    def setUp(self):
        self.amazon = AmazonMediaStorage(self.app)

        # Patch config with defaults
        p = patch.dict(self.app.config, {
            'AMAZON_CONTAINER_NAME': 'acname',
            'AMAZON_REGION': 'us-east-1',
            'AMAZON_S3_USE_HTTPS': True,
            'AMAZON_SERVE_DIRECT_LINKS': True,
            'AMAZON_SERVER': 'amazonaws.com',
            'AMAZON_S3_SUBFOLDER': '',
        })
        p.start()
        self.addCleanup(p.stop)

    def test_media_id(self):
        filename = 'test'
        # automatic version is set on 15mins granularity.
        mins_granularity = int(int(time.strftime('%M')) / 4) * 4
        time_id = '%s%s' % (time.strftime('%Y%m%d%H%m'), mins_granularity)
        media_id = self.amazon.media_id(filename)
        self.assertEqual('%s/%s' % (time_id, filename), media_id)

        sub = 'test-sub'
        with patch.dict(self.app.config, {'AMAZON_S3_SUBFOLDER': sub}):
            media_id = self.amazon.media_id(filename)
            self.assertEqual('%s/%s/%s' % (sub, time_id, filename), media_id)

    def test_url_for_media(self):
        media_id = 'test'
        self.assertEqual(
            self.amazon.url_for_media(media_id),
            'https://acname.s3-us-east-1.amazonaws.com/%s' % media_id
        )

        with patch.dict(self.app.config, {'AMAZON_S3_USE_HTTPS': False}):
            self.assertEqual(
                self.amazon.url_for_media(media_id),
                'http://acname.s3-us-east-1.amazonaws.com/%s' % media_id
            )

        with patch.dict(self.app.config, {'AMAZON_REGION': 'eu-west-1'}):
            self.assertEqual(
                self.amazon.url_for_media(media_id),
                'https://acname.s3-eu-west-1.amazonaws.com/%s' % media_id
            )


class AmazonMediaStoragePutAndDeleteTest(TestCase):
    def setUp(self):
        self.amazon = AmazonMediaStorage(self.app)

    def test_put_and_delete(self):
        """Test amazon if configured.

        If the environment variables have a Amazon secret key set then assume
        that we can attempt to put and delete into s3

        :return:
        """
        if self.app.config['AMAZON_SECRET_ACCESS_KEY']:
            id = self.amazon.put('test', content_type='text/plain')
            self.assertIsNot(id, None)
            self.assertTrue(self.amazon.exists(id))
            fromS3 = self.amazon.get(id)
            self.assertEqual(fromS3.read().decode('utf-8'), 'test')
            self.amazon.delete(id)
            self.assertFalse(self.amazon.exists(id))
        else:
            self.assertTrue(True)
