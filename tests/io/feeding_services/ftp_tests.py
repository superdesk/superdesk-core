# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import glob
import os
import shutil
import tempfile
import unittest
from unittest import mock
import datetime
import pytz

from superdesk.io.feeding_services import ftp
from superdesk.utc import utcnow

PREFIX = 'test_superdesk_'
PROVIDER = {
    "_id": "test_provider",
    "config": {
        "passive": True,
        "username": "user",
        "password": "password",
        "host": "example.net",
        "dest_path": "/tmp",
        "path": "",
        "move": True,
        "move_path": "dest_move",
        "move_path_error": "error",
        "field_aliases": []
    },
    "last_updated": datetime.datetime(2017, 5, 16, 16, 47, 39, tzinfo=pytz.utc),
    "last_item_update": datetime.datetime(2017, 5, 16, 16, 47, 39, tzinfo=pytz.utc)
}


def _exception(*args, **kwargs):
    """Raise an exception on call, for testing purpose"""
    raise Exception('Test exception')


def ftp_file(filename):
    facts = mock.Mock()
    facts.get.return_value = 'file'
    facts.__getitem__ = mock.Mock(return_value="20170517164739")
    return [filename, facts]


class FakeFTP(mock.MagicMock):

    files = [ftp_file('filename.xml')]

    def mlsd(self, path=""):
        return iter(self.files)

    def cwd(self, path):
        pass


class FTPTestCase(unittest.TestCase):

    def test_it_can_connect(self):
        service = ftp.FTPFeedingService()

        if 'FTP_URL' not in os.environ:
            return

        config = service.config_from_url(os.environ['FTP_URL'])
        self.assertEqual('test', config['path'])
        self.assertEqual('localhost', config['host'])

        config['dest_path'] = tempfile.mkdtemp(prefix=PREFIX)
        provider = {'config': config}

        items = service._update(provider, {})
        self.assertEqual(266, len(items))

        provider['last_updated'] = utcnow()
        self.assertEqual(0, len(service._update(provider, {})))

        self.assertTrue(os.path.isdir(provider['config']['dest_path']))
        self.assertEqual(266, len(os.listdir(provider['config']['dest_path'])))

    def tearDown(self):
        for folder in glob.glob('/tmp/%s*' % (PREFIX)):
            shutil.rmtree(folder)

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', mock.Mock())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested(self, ftp_connect):
        """Check that ingested file is moved if "move" is set

        feature requested in SDESK-468
        """
        provider = PROVIDER.copy()
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        mock_ftp.rename.assert_called_once_with('filename.xml', 'dest_move/filename.xml')

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', mock.Mock())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested_default(self, ftp_connect):
        """Check that ingested file is moved to default path if "move" is empty string

        feature requested in SDESK-1452
        """
        provider = PROVIDER.copy()
        provider['config']['move_path'] = ""
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        dest_path = os.path.join(ftp.DEFAULT_SUCCESS_PATH, "filename.xml")
        mock_ftp.rename.assert_called_once_with('filename.xml', dest_path)

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', mock.Mock())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested_no_move(self, ftp_connect):
        """Check that ingested file is not moved if "move" is not set

        feature requested in SDESK-468
        """
        provider = PROVIDER.copy()
        provider['config']['move'] = False
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        mock_ftp.rename.assert_not_called()

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', _exception)
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_error(self, ftp_connect):
        """Check that error on ingestion moves item if "move_path_error" is set

        feature requested in SDESK-1452
        """
        provider = PROVIDER.copy()
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        mock_ftp.rename.assert_called_once_with('filename.xml', 'error/filename.xml')

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', _exception)
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_error_default(self, ftp_connect):
        """Check that error on ingestion use default path if "move_path_error" is empty string

        feature requested in SDESK-1452
        """
        provider = PROVIDER.copy()
        provider['config']['move_path_error'] = ""
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        dest_path = os.path.join(ftp.DEFAULT_FAILURE_PATH, "filename.xml")
        mock_ftp.rename.assert_called_once_with('filename.xml', dest_path)

    def test_allowed_suffix_json(self):
        """Check that json files are allowed for ingestion."""
        service = ftp.FTPFeedingService()
        self.assertFalse(service._is_allowed('foo.jpg'))
        self.assertTrue(service._is_allowed('foo.xml'))
        self.assertTrue(service._is_allowed('foo.json'))
        self.assertTrue(service._is_allowed('foo.JSON'))
        self.assertFalse(service._is_allowed('foojson'))
        self.assertFalse(service._is_allowed('foo.json.tar.gz'))
