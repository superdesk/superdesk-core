from unittest.mock import Mock, call
from datetime import timedelta

from superdesk.tests import TestCase
from superdesk.utc import utcnow
from superdesk.utc import query_datetime

from superdesk.commands.remove_exported_files import RemoveExportedFiles


class MockMediaFS:
    """Simple Mocked Media FS"""

    def __init__(self, files):
        self.files = files
        self.delete = Mock()
        self.delete.side_effect = self._delete
        self.find = Mock()
        self.find.side_effect = self._find

    def _delete(self, _id):
        del self.files[_id]

    def _find(self, folder=None, upload_date=None):
        files = []
        for file in self.files.values():
            if (upload_date is not None and not query_datetime(file['upload_date'], upload_date)) \
                    or not file['filename'].startswith(folder):
                continue
            files.append(file)
        return files


class RemoveExportedFilesTest(TestCase):

    def setUp(self):
        # Create a backup of the original media reference so we can set it back up again later
        self.original_media = self.app.media
        self.now = utcnow()
        self.app.media = MockMediaFS({
            'a1': {'_id': 'a1', 'filename': 'aa', 'upload_date': self.now},
            'b2': {'_id': 'b2', 'filename': 'bb', 'upload_date': self.now - timedelta(hours=20)},
            'c3': {'_id': 'c3', 'filename': 'cc', 'upload_date': self.now - timedelta(hours=25)},
            'd4': {'_id': 'd4', 'filename': 'dd', 'upload_date': self.now - timedelta(hours=36)},
            'e5': {'_id': 'e5', 'filename': 'temp/ee', 'upload_date': self.now},
            'f6': {'_id': 'f6', 'filename': 'temp/ff', 'upload_date': self.now - timedelta(hours=20)},
            'g7': {'_id': 'g7', 'filename': 'temp/gg', 'upload_date': self.now - timedelta(hours=25)},
            'h8': {'_id': 'h8', 'filename': 'temp/hh', 'upload_date': self.now - timedelta(hours=36)}
        })
        self.can_expire = ['g7', 'h8']

        self.command = RemoveExportedFiles()

    def tearDown(self):
        """Ensure to restore the original media reference"""
        self.app.media = self.original_media

    def test_get_file_ids(self):
        expire_at = utcnow() - timedelta(hours=24)
        for file_id in self.command._get_file_ids(expire_at):
            self.assertIn(file_id, self.can_expire)

        kwargs = {
            'folder': 'temp',
            'upload_date': {'$lte': expire_at}
        }
        self.app.media.find.assert_called_once_with(**kwargs)

    def test_remove_exported_files(self):
        expire_at = utcnow() - timedelta(hours=24)
        self.command._remove_exported_files(expire_at)

        for file_id in self.app.media.files:
            self.assertNotIn(file_id, self.can_expire)

        self.app.media.delete.assert_has_calls([call('g7'), call('h8')], any_order=True)
        self.assertEqual(self.app.media.delete.call_count, 2)

    def test_run(self):
        self.command.run()
        for file_id in self.app.media.files:
            self.assertNotIn(file_id, self.can_expire)

        self.app.media.delete.assert_has_calls([call('g7'), call('h8')], any_order=True)
        self.assertEqual(self.app.media.delete.call_count, 2)
