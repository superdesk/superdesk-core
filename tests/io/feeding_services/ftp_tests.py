# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import copy
import glob
import os
import shutil
import tempfile
from unittest import mock
import datetime
import pytz

from superdesk.tests import setup
from superdesk.tests import TestCase as CoreTestCase
from superdesk.io.feeding_services import ftp
from superdesk.utc import utcnow, utc

PREFIX = 'test_superdesk_'
PROVIDER = {
    "_id": "test_provider",
    "name": "Test provider",
    "config": {
        "passive": True,
        "username": "user",
        "password": "password",
        "host": "example.net",
        "dest_path": "/tmp",
        "path": "",
        "move": True,
        "ftp_move_path": "dest_move",
        "move_path_error": "error",
        "field_aliases": []
    },
    "last_updated": datetime.datetime(2017, 5, 16, 16, 47, 39, tzinfo=pytz.utc),
    "last_item_update": datetime.datetime(2017, 5, 16, 16, 47, 39, tzinfo=pytz.utc)
}


def ftp_file(filename, modify):
    facts = mock.Mock()
    facts.get.return_value = 'file'
    facts.__getitem__ = mock.Mock(return_value=modify)
    return [filename, facts]


def ingest_items(generator, ingest_status=True):
    failed = None
    while True:
        try:
            item = generator.send(failed)
            failed = set([item['guid']]) if not ingest_status else set()
        except StopIteration:
            break


class FakeFTP(mock.MagicMock):

    files = [
        ftp_file('filename_1.xml', '20170517164739'),
        ftp_file('filename_2.xml', '20170517164739'),
        ftp_file('filename_3.xml', '20170517164739'),
        ftp_file('filename_4.xml', '20170517164739'),
        ftp_file('filename_5.xml', '20170517164745'),
        ftp_file('filename_6.xml', '20170517164745'),
        ftp_file('filename_7.xml', '20170517164745'),
        ftp_file('filename_8.xml', '20170517164745'),
        ftp_file('filename_9.xml', '20170517164746'),
        ftp_file('filename_10.xml', '20170517164748'),
        ftp_file('filename_11.xml', '20170517164748'),
        ftp_file('filename_12.xml', '20170517164748'),
        ftp_file('filename_13.xml', '20170517164748'),
        ftp_file('filename_14.xml', '20170517164748'),
        ftp_file('filename_15.xml', '20170517164755'),
        ftp_file('filename_16.xml', '20170517164756')
    ]

    def mlsd(self, path=""):
        return iter(self.files)

    def cwd(self, path):
        pass


class FakeFTPRecentFiles(FakeFTP):

    files = [
        ftp_file('old_file.xml', '20170517164756'),
        # we need a file ingested now, before INGEST_OLD_CONTENT_MINUTES is expired
        ftp_file('recent_file.xml', datetime.datetime.today().strftime('%Y%m%d%H%M%S')),
    ]


class FakeFeedParser(mock.MagicMock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        del self.ALLOWED_EXT


class FailingFakeFeedParser(FakeFeedParser):

    def parse(self, *args, **kwargs):
        raise Exception('Test exception')


class TestCase(CoreTestCase):

    def setUpForChildren(self):
        """Run this `setUp` stuff for each children.

        Configure new `app` for each test.
        """
        setup.reset = True
        setup(self)

        self.ctx = self.app.app_context()
        self.ctx.push()

        def clean_ctx():
            if self.ctx:
                self.ctx.pop()

        self.addCleanup(clean_ctx)


class FTPTestCase(TestCase):

    def test_it_can_connect(self):
        service = ftp.FTPFeedingService()

        if 'FTP_URL' not in os.environ:
            return

        config = service.config_from_url(os.environ['FTP_URL'])
        self.assertEqual('test', config['path'])
        self.assertEqual('localhost', config['host'])

        config['dest_path'] = tempfile.mkdtemp(prefix=PREFIX)
        provider = {'config': config}

        items = service.update(provider, {})
        self.assertEqual(266, len(items))

        provider['last_updated'] = utcnow()
        self.assertEqual(0, len(service.update(provider, {})))

        self.assertTrue(os.path.isdir(provider['config']['dest_path']))
        self.assertEqual(266, len(os.listdir(provider['config']['dest_path'])))

    def tearDown(self):
        for folder in glob.glob('/tmp/%s*' % (PREFIX)):
            shutil.rmtree(folder)

    @mock.patch.object(os.path, 'getsize', return_value=3)
    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested(self, ftp_connect, *args):
        """Check that ingested file is moved if "move" is set

        feature requested in SDESK-468
        """
        provider = copy.deepcopy(PROVIDER)
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        ingest_items(service.update(provider, {}))

        mock_ftp = ftp_connect.return_value.__enter__.return_value

        self.assertEqual(mock_ftp.rename.call_count, len(FakeFTP.files))
        for i, call in enumerate(mock_ftp.rename.call_args_list):
            self.assertEqual(
                call[0],
                (FakeFTP.files[i][0], 'dest_move/{}'.format(FakeFTP.files[i][0]))
            )

    @mock.patch.object(os.path, 'getsize', return_value=3)
    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested_default(self, ftp_connect, *args):
        """Check that ingested file is moved to default path if "move" is empty string

        feature requested in SDESK-1452
        """
        provider = copy.deepcopy(PROVIDER)
        provider['config']['ftp_move_path'] = ""
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        ingest_items(service.update(provider, {}))
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        self.assertEqual(mock_ftp.rename.call_count, len(FakeFTP.files))
        for i, call in enumerate(mock_ftp.rename.call_args_list):
            self.assertEqual(
                call[0],
                (FakeFTP.files[i][0], '{}/{}'.format(ftp.DEFAULT_SUCCESS_PATH, FakeFTP.files[i][0]))
            )

    @mock.patch.object(os.path, 'getsize', return_value=3)
    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested_error(self, ftp_connect, *args):
        """Check that ingested file is moved to error path if ingest fails"""
        provider = copy.deepcopy(PROVIDER)
        provider['config']['ftp_move_path'] = ""
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        ingest_items(service.update(provider, {}), False)
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        self.assertEqual(mock_ftp.rename.call_count, len(FakeFTP.files))
        for i, call in enumerate(mock_ftp.rename.call_args_list):
            self.assertEqual(
                call[0],
                (FakeFTP.files[i][0], '{}/{}'.format('error', FakeFTP.files[i][0]))
            )

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_ingested_no_move(self, ftp_connect):
        """Check that ingested file is not moved if "move" is not set

        feature requested in SDESK-468
        """
        provider = copy.deepcopy(PROVIDER)
        provider['config']['move'] = False
        service = ftp.FTPFeedingService()
        ingest_items(service.update(provider, {}))
        mock_ftp = ftp_connect.return_value.__enter__.return_value
        mock_ftp.rename.assert_not_called()

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTPRecentFiles)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_backstop(self, ftp_connect):
        """Check that failing file is not moved if it's more recent thant INGEST_OLD_CONTENT_MINUTES"""
        provider = copy.deepcopy(PROVIDER)
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        ingest_items(service.update(provider, {}))
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        # recent_file must not have been ingested
        self.assertEqual(mock_ftp.rename.call_count, len(FakeFTPRecentFiles.files) - 1)
        for i, call in enumerate(mock_ftp.rename.call_args_list):
            self.assertNotEqual(
                call[0][0],
                'recent_file.xml',
            )

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FailingFakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_error(self, ftp_connect):
        """Check that error on ingestion moves item if "move_path_error" is set

        feature requested in SDESK-1452
        """
        provider = copy.deepcopy(PROVIDER)
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        ingest_items(service.update(provider, {}))
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        self.assertEqual(mock_ftp.rename.call_count, len(FakeFTP.files))
        for i, call in enumerate(mock_ftp.rename.call_args_list):
            self.assertEqual(
                call[0],
                (FakeFTP.files[i][0], 'error/{}'.format(FakeFTP.files[i][0]))
            )

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FailingFakeFeedParser())
    @mock.patch('builtins.open', mock.mock_open())
    def test_move_error_default(self, ftp_connect):
        """Check that error on ingestion use default path if "move_path_error" is empty string

        feature requested in SDESK-1452
        """
        provider = copy.deepcopy(PROVIDER)
        provider['config']['move_path_error'] = ""
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        ingest_items(service.update(provider, {}))
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        self.assertEqual(mock_ftp.rename.call_count, len(FakeFTP.files))
        for i, call in enumerate(mock_ftp.rename.call_args_list):
            self.assertEqual(
                call[0],
                (FakeFTP.files[i][0], '{}/{}'.format(ftp.DEFAULT_FAILURE_PATH, FakeFTP.files[i][0]))
            )

    def test_allowed_suffix_json(self):
        """Check that json files are allowed for ingestion."""
        service = ftp.FTPFeedingService()
        allowed = ftp.FTPFeedingService.ALLOWED_EXT_DEFAULT
        self.assertFalse(service._is_allowed('foo.jpg', allowed))
        self.assertTrue(service._is_allowed('foo.xml', allowed))
        self.assertTrue(service._is_allowed('foo.json', allowed))
        self.assertTrue(service._is_allowed('foo.JSON', allowed))
        self.assertFalse(service._is_allowed('foojson', allowed))
        self.assertFalse(service._is_allowed('foo.json.tar.gz', allowed))

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch.object(ftp.FTPFeedingService, '_retrieve_and_parse')
    def test_files_limit_no_move(self, *mocks):
        """Test file limits when move is off

        feature requested in SDESK-3815
        """
        update = {}
        self.app.config['FTP_INGEST_FILES_LIST_LIMIT'] = 3

        retrieve_and_parse, ftp_connect = mocks
        provider = copy.deepcopy(PROVIDER)
        provider['config']['move'] = False
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        ingest_items(service.update(provider, update))
        provider.update(update)
        self.assertEqual(retrieve_and_parse.call_count, 3)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164739', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        self.assertEqual(retrieve_and_parse.call_count, 8)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164745', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        self.assertEqual(retrieve_and_parse.call_count, 13)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164746', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        self.assertEqual(retrieve_and_parse.call_count, 16)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164748', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        self.assertEqual(retrieve_and_parse.call_count, 22)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164755', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        self.assertEqual(retrieve_and_parse.call_count, 24)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164756', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        self.assertEqual(mock_ftp.rename.call_count, 0)

    @mock.patch.object(ftp, 'ftp_connect', new_callable=FakeFTP)
    @mock.patch.object(ftp.FTPFeedingService, 'get_feed_parser', FakeFeedParser())
    @mock.patch.object(ftp.FTPFeedingService, '_retrieve_and_parse')
    def test_files_limit_move(self, *mocks):
        """Test file limits when move is on

        feature requested in SDESK-3815
        """
        update = {}
        self.app.config['FTP_INGEST_FILES_LIST_LIMIT'] = 3

        retrieve_and_parse, ftp_connect = mocks
        provider = copy.deepcopy(PROVIDER)
        service = ftp.FTPFeedingService()
        service._is_empty = mock.MagicMock(return_value=False)
        mock_ftp = ftp_connect.return_value.__enter__.return_value

        ingest_items(service.update(provider, update))
        provider.update(update)
        # emulate moving files by reducing list
        ftp_connect().__enter__().mlsd = mock.Mock()
        ftp_connect().__enter__().mlsd.return_value = iter(FakeFTP.files[3:])

        self.assertEqual(retrieve_and_parse.call_count, 3)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164739', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        # emulate moving files by reducing list
        ftp_connect().__enter__().mlsd = mock.Mock()
        ftp_connect().__enter__().mlsd.return_value = iter(FakeFTP.files[6:])

        self.assertEqual(retrieve_and_parse.call_count, 6)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164745', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        # emulate moving files by reducing list
        ftp_connect().__enter__().mlsd = mock.Mock()
        ftp_connect().__enter__().mlsd.return_value = iter(FakeFTP.files[9:])

        self.assertEqual(retrieve_and_parse.call_count, 9)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164746', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        # emulate moving files by reducing list
        ftp_connect().__enter__().mlsd = mock.Mock()
        ftp_connect().__enter__().mlsd.return_value = iter(FakeFTP.files[12:])

        self.assertEqual(retrieve_and_parse.call_count, 12)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164748', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        # emulate moving files by reducing list
        ftp_connect().__enter__().mlsd = mock.Mock()
        ftp_connect().__enter__().mlsd.return_value = iter(FakeFTP.files[15:])

        self.assertEqual(retrieve_and_parse.call_count, 15)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164755', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        ingest_items(service.update(provider, update))
        provider.update(update)
        # emulate moving files by reducing list
        ftp_connect().__enter__().mlsd = mock.Mock()
        ftp_connect().__enter__().mlsd.return_value = iter(FakeFTP.files[16:])

        self.assertEqual(retrieve_and_parse.call_count, 16)
        self.assertEqual(
            provider['private']['last_processed_file_modify'],
            datetime.datetime.strptime('20170517164756', '%Y%m%d%H%M%S').replace(tzinfo=utc)
        )

        self.assertEqual(mock_ftp.rename.call_count, 16)
