import os
import time

from datetime import timedelta
from unittest.mock import patch, Mock

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from superdesk.storage import AmazonMediaStorage
from superdesk.media.media_operations import guess_media_extension


class AmazonMediaStorageTestCase(TestCase):

    def setUp(self):
        self.amazon = AmazonMediaStorage(self.app)

        # Patch config with defaults
        p = patch.dict(self.app.config, {
            'AMAZON_SECRET_ACCESS_KEY': None,
            'AMAZON_CONTAINER_NAME': 'acname',
            'AMAZON_REGION': 'us-east-1',
            'AMAZON_S3_SUBFOLDER': '',
            'MEDIA_PREFIX': 'https://acname.s3-us-east-1.amazonaws.com'
        })
        p.start()
        self.addCleanup(p.stop)

    def test_media_url(self):
        filename = 'test'
        # automatic version is set on 15mins granularity.
        mins_granularity = int(int(time.strftime('%M')) / 4) * 4
        time_id = '%s%s' % (time.strftime('%Y%m%d%H%m'), mins_granularity)
        media_id = self.amazon.media_id(filename)
        self.assertEqual('%s/%s' % (time_id, filename), media_id)
        self.assertEqual(
            self.amazon.url_for_media(media_id),
            'https://acname.s3-us-east-1.amazonaws.com/%s' % media_id
        )
        sub = 'test-sub'
        settings = {
            'AMAZON_S3_SUBFOLDER': sub,
            'MEDIA_PREFIX': 'https://acname.s3-us-east-1.amazonaws.com/' + sub
        }
        with patch.dict(self.app.config, settings):
            media_id = self.amazon.media_id(filename)
            self.assertEqual('%s/%s' % (time_id, filename), media_id)
            path = '%s/%s' % (sub, media_id)
            self.assertEqual(
                self.amazon.url_for_media(media_id),
                'https://acname.s3-us-east-1.amazonaws.com/%s' % path
            )
            with patch.object(self.amazon, 'client') as s3:
                self.amazon.get(media_id)
                self.assertTrue(s3.get_object.called)
                self.assertEqual(
                    s3.get_object.call_args[1],
                    dict(Bucket='acname', Key=path)
                )

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

    def test_put_into_folder(self):
        data = b'test data'
        folder = 's3test'
        filename = 'abc123.zip'
        content_type = 'application/zip'
        self.amazon.client.put_object = Mock()
        self.amazon.media_id = Mock(return_value=filename)
        self.amazon._check_exists = Mock(return_value=False)

        self.amazon.put(data, filename, content_type, folder=folder)

        kwargs = {
            'Key': '{}/{}'.format(folder, filename),
            'Body': data,
            'Bucket': 'acname',
            'ContentType': content_type,
        }
        self.amazon.client.put_object.assert_called_once_with(**kwargs)

    def test_find_folder(self):
        self.amazon.client = Mock()

        # Mock getting list of files from Amazon, first request returns a file, second request returns empty list
        self.amazon.client.list_objects = Mock(side_effect=[
            {'Contents': [{
                'Key': 'gridtest/abcd1234',
                'LastModified': utcnow() - timedelta(minutes=30),
                'Size': 500,
                'ETag': 'abcd1234'
            }]},
            {'Contents': []}
        ])

        folder = 'gridtest'
        self.amazon.find(folder=folder)

        call_arg_list = [({
            'Bucket': 'acname',
            'Marker': '',
            'MaxKeys': 1000,
            'Prefix': '{}/'.format(folder)
        },), ({
            'Bucket': 'acname',
            'Marker': 'gridtest/abcd1234',
            'MaxKeys': 1000,
            'Prefix': '{}/'.format(folder)
        },)]

        # We test the call_args_list as self.amazon.client.list_objects would have been called twice
        self.assertEqual(self.amazon.client.list_objects.call_count, 2)
        self.assertEqual(self.amazon.client.list_objects.call_args_list, call_arg_list)

    def test_guess_extension(self):
        self.assertEqual('.jpg', guess_media_extension('image/jpeg'))
        self.assertEqual('.png', guess_media_extension('image/png'))

        self.assertEqual('.mp3', guess_media_extension('audio/mp3'))
        self.assertEqual('.mp3', guess_media_extension('audio/mpeg'))
        self.assertEqual('.flac', guess_media_extension('audio/flac'))

        self.assertEqual('.mp4', guess_media_extension('video/mp4'))

        # leave empty when there is no extension
        self.assertEqual('', guess_media_extension('audio/foo'))

    def test_media_url_none_utf8(self):
        filename = '[DIARY NOTE] – Victory In The Pacific Day Commemoration - Thursday (1)'
        # automatic version is set on 15mins granularity.
        mins_granularity = int(int(time.strftime('%M')) / 4) * 4
        time_id = '%s%s' % (time.strftime('%Y%m%d%H%m'), mins_granularity)
        media_id = self.amazon.media_id(filename)
        self.assertEqual('%s/%s' % (time_id, 'DIARY NOTE - Victory In The Pacific Day Commemoration - Thursday (1)'),
                         media_id)
        self.assertEqual(
            self.amazon.url_for_media(media_id),
            'https://acname.s3-us-east-1.amazonaws.com/%s' % media_id
        )
        sub = 'test-sub'
        settings = {
            'AMAZON_S3_SUBFOLDER': sub,
            'MEDIA_PREFIX': 'https://acname.s3-us-east-1.amazonaws.com/' + sub
        }
        with patch.dict(self.app.config, settings):
            media_id = self.amazon.media_id(filename)
            self.assertEqual(
                '%s/%s' % (time_id, 'DIARY NOTE - Victory In The Pacific Day Commemoration - Thursday (1)'), media_id)
            path = '%s/%s' % (sub, media_id)
            self.assertEqual(
                self.amazon.url_for_media(media_id),
                'https://acname.s3-us-east-1.amazonaws.com/%s' % path
            )
            with patch.object(self.amazon, 'client') as s3:
                self.amazon.get(media_id)
                self.assertTrue(s3.get_object.called)
                self.assertEqual(
                    s3.get_object.call_args[1],
                    dict(Bucket='acname', Key=path)
                )

    def test_put_into_folder_none_utf8(self):
        data = b'test data'
        folder = 's3test'
        filename = '[DIARY NOTE] – Victory In The Pacific Day Commemoration - Thursday (1).pdf'
        content_type = 'application/pdf'
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)

        self.amazon.put(data, filename, content_type, folder=folder, version=False)

        kwargs = {
            'Key': '{}/{}'.format(folder, 'DIARY NOTE - Victory In The Pacific Day Commemoration - Thursday (1).pdf'),
            'Body': data,
            'Bucket': 'acname',
            'ContentType': content_type,
        }
        self.amazon.client.put_object.assert_called_once_with(**kwargs)

    def test_get_none_utf8(self):
        self.amazon.client.get_object = Mock()
        self.amazon.extract_metadata_from_headers = Mock(return_value={})

        self.amazon.get('[DIARY NOTE] – Victory In The Pacific Day Commemoration - Thursday (1).pdf')

        kwargs = {
            'Bucket': 'acname',
            'Key': 'DIARY NOTE - Victory In The Pacific Day Commemoration - Thursday (1).pdf'
        }
        self.amazon.client.get_object.assert_called_once_with(**kwargs)

    def test_mimetype_detect(self):
        # keep default mimetype
        content = b'bytes are here'
        filename = 'extensionless'
        content_type = 'text/css'
        folder = 'f1'
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)
        self.amazon.media_id = Mock(return_value=filename)
        self.amazon.put(content, filename, content_type, folder=folder)
        self.amazon.client.put_object.assert_called_once_with(
            **{
                'Key': '{}/{}'.format(folder, filename),
                'Body': content,
                'Bucket': 'acname',
                'ContentType': content_type
            }
        )

        # get mimetype from the filename
        content = b'bytes are here'
        filename = 'styles.css'
        content_type = 'application/pdf'
        folder = 'f1'
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)
        self.amazon.media_id = Mock(return_value=filename)
        self.amazon.put(content, filename, content_type, folder=folder)
        self.amazon.client.put_object.assert_called_once_with(
            **{
                'Key': '{}/{}'.format(folder, filename),
                'Body': b'bytes are here',
                'Bucket': 'acname',
                'ContentType': 'text/css'
            }
        )

        content = b'bytes are here'
        filename = 'styles.JpG'
        content_type = 'application/pdf'
        folder = 'f1'
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)
        self.amazon.media_id = Mock(return_value=filename)
        self.amazon.put(content, filename, content_type, folder=folder)
        self.amazon.client.put_object.assert_called_once_with(
            **{
                'Key': '{}/{}'.format(folder, filename),
                'Body': b'bytes are here',
                'Bucket': 'acname',
                'ContentType': 'image/jpeg'
            }
        )

        # get mimetype from the file
        fixtures_path = os.path.join(os.path.dirname(__file__), 'fixtures')

        with open(os.path.join(fixtures_path, "file_example-jpg.jpg"), 'rb') as content:
            filename = 'extensionless'
            content_type = 'dummy/text'
            folder = 'f1'
            self.amazon.client.put_object = Mock()
            self.amazon._check_exists = Mock(return_value=False)
            self.amazon.media_id = Mock(return_value=filename)
            self.amazon.put(content, filename, content_type, folder=folder)
            self.amazon.client.put_object.assert_called_once_with(
                **{
                    'Key': '{}/{}'.format(folder, filename),
                    'Body': content,
                    'Bucket': 'acname',
                    'ContentType': 'image/jpeg'
                }
            )

            with open(os.path.join(fixtures_path, "file_example-xls.xls"), 'rb') as content:
                filename = 'extensionless'
                content_type = 'dummy/text'
                folder = 'f1'
                self.amazon.client.put_object = Mock()
                self.amazon._check_exists = Mock(return_value=False)
                self.amazon.media_id = Mock(return_value=filename)
                self.amazon.put(content, filename, content_type, folder=folder)
                self.amazon.client.put_object.assert_called_once_with(
                    **{
                        'Key': '{}/{}'.format(folder, filename),
                        'Body': content,
                        'Bucket': 'acname',
                        'ContentType': 'application/vnd.ms-excel'
                    }
                )

            with open(os.path.join(fixtures_path, "file_example-xlsx.xlsx"), 'rb') as content:
                filename = 'extensionless'
                content_type = 'dummy/text'
                folder = 'f1'
                self.amazon.client.put_object = Mock()
                self.amazon._check_exists = Mock(return_value=False)
                self.amazon.media_id = Mock(return_value=filename)
                self.amazon.put(content, filename, content_type, folder=folder)
                self.amazon.client.put_object.assert_called_once_with(
                    **{
                        'Key': '{}/{}'.format(folder, filename),
                        'Body': content,
                        'Bucket': 'acname',
                        'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    }
                )

            with open(os.path.join(fixtures_path, "file_example-docx.docx"), 'rb') as content:
                filename = 'extensionless'
                content_type = 'dummy/text'
                folder = 'f1'
                self.amazon.client.put_object = Mock()
                self.amazon._check_exists = Mock(return_value=False)
                self.amazon.media_id = Mock(return_value=filename)
                self.amazon.put(content, filename, content_type, folder=folder)
                self.amazon.client.put_object.assert_called_once_with(
                    **{
                        'Key': '{}/{}'.format(folder, filename),
                        'Body': content,
                        'Bucket': 'acname',
                        'ContentType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    }
                )
