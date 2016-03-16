# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.storage.amazon.amazon_media_storage import AmazonMediaStorage
from unittest import mock
import unittest
from unittest.mock import MagicMock


class AmazonMediaStorageTestCase(unittest.TestCase):
    config = {
        'AMAZON_CONTAINER_NAME': 'test_container',
        'AMAZON_REGION': 'test_region',
        'AMAZON_ACCESS_KEY_ID': 'test_key',
        'AMAZON_SECRET_ACCESS_KEY': 'secret_key',
        'AMAZON_SERVE_DIRECT_LINKS': True,
        'AMAZON_S3_USE_HTTPS': False,
        'AMAZON_SERVER': 'amazonaws.com',
        'AMAZON_PROXY_SERVER': 's3.proxy.com',
        'AMAZON_URL_GENERATOR': 'default',
        'AMAZON_URL_VERSION': 'v2'
    }

    @mock.patch('superdesk.storage.amazon.amazon_media_storage.boto3', MagicMock())
    def test_url_for_media(self):
        app = MagicMock()
        app.config = self.config
        url = AmazonMediaStorage(app).url_for_media('media_id', 'image/jpeg')
        self.assertEqual(url, 'http://s3.proxy.com/v2/test_container.s3-test_region.amazonaws.com/media_id.jpg')

        app.config['AMAZON_S3_USE_HTTPS'] = True
        url = AmazonMediaStorage(app).url_for_media('media_id', 'image/jpeg')
        self.assertEqual(url, 'https://s3.proxy.com/v2/test_container.s3-test_region.amazonaws.com/media_id.jpg')

        app.config['AMAZON_URL_GENERATOR'] = 'partial'
        url = AmazonMediaStorage(app).url_for_media('media_id', 'image/jpeg')
        self.assertEqual(url, 'https://s3.proxy.com/v2/media_id.jpg')
