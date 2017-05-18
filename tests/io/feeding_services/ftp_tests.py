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
        "field_aliases": []
    },
    "last_updated": datetime.datetime(2017, 5, 16, 16, 47, 39, tzinfo=pytz.utc),
    "last_item_update": datetime.datetime(2017, 5, 16, 16, 47, 39, tzinfo=pytz.utc)
}


class FakeFTP(mock.MagicMock):

    def mlsd(self):
        facts = mock.Mock()
        facts.get.return_value = 'file'
        facts.__getitem__ = mock.Mock(return_value="20170517164739")
        return [['filename.xml', facts]]


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
        """Check that ingested file is moved if (and only if) "move" is set

        feature requested in SDESK-468
        """
        provider = PROVIDER.copy()
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        mock_ftp.rename.assert_called_with('filename.xml', 'dest_move/filename.xml')
        # we do the same test by reseting mock_ftp
        # and setting move to False, this time rename must not be called
        provider['config']['move'] = False
        ftp_connect.return_value.__enter__.return_value = mock.MagicMock()
        service = ftp.FTPFeedingService()
        service._update(provider, {})
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        mock_ftp.rename.assert_not_called()
