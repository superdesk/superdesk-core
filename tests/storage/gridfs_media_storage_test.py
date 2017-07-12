
import io
import eve
import bson
import unittest
from unittest.mock import Mock
from superdesk.upload import bp, upload_url
from superdesk.datalayer import SuperdeskDataLayer
from superdesk.storage import SuperdeskGridFSMediaStorage
from superdesk.utc import utcnow
from datetime import timedelta


class GridFSMediaStorageTestCase(unittest.TestCase):

    def setUp(self):
        self.app = eve.Eve(__name__, {'DOMAIN': {}})
        self.app.config['SERVER_NAME'] = 'localhost'
        self.app.config['DOMAIN'] = {'upload': {}}
        self.app.config['MONGO_DBNAME'] = 'sptests'
        self.app.data = SuperdeskDataLayer(self.app)
        self.media = SuperdeskGridFSMediaStorage(self.app)
        self.app.register_blueprint(bp)
        self.app.upload_url = upload_url

    def test_media_id(self):
        filename = 'some-file'
        media_id = self.media.media_id(filename)
        self.assertIsInstance(media_id, bson.ObjectId)
        self.assertEqual(media_id, self.media.media_id(filename))

    def test_url_for_media(self):
        _id = self.media.media_id('test')
        with self.app.app_context():
            url = self.media.url_for_media(_id)
        self.assertEqual('http://localhost/upload-raw/%s' % _id, url)

    def test_put_media_with_id(self):
        data = io.StringIO("test data")
        filename = 'x'

        gridfs = self._mock_gridfs()
        _id = bson.ObjectId()

        with self.app.app_context():
            self.media.put(data, filename, 'text/plain', _id=str(_id))

        kwargs = {
            'content_type': 'text/plain',
            'filename': filename,
            'metadata': None,
            '_id': _id,
        }

        gridfs.put.assert_called_once_with(data, **kwargs)

    def test_put_into_folder(self):
        data = b'test data'
        filename = 'x'
        folder = 'gridtest'

        gridfs = self._mock_gridfs()

        with self.app.app_context():
            self.media.put(data, filename=filename, content_type='text/plain', folder=folder)

        kwargs = {
            'content_type': 'text/plain',
            'filename': '{}/{}'.format(folder, filename),
            'metadata': None
        }

        gridfs.put.assert_called_once_with(data, **kwargs)

    def test_find_files(self):
        gridfs = self._mock_gridfs()
        upload_date = {'$lte': utcnow(), '$gte': utcnow() - timedelta(hours=1)}
        folder = 'gridtest'
        query_filename = {'filename': {'$regex': '^{}/'.format(folder)}}
        query_upload_date = {'uploadDate': upload_date}

        with self.app.app_context():
            self.media.find(folder=folder, upload_date=upload_date)
            gridfs.find.assert_called_once_with({'$and': [query_filename, query_upload_date]})

            self.media.find(folder=folder)
            gridfs.find.assert_called_with(query_filename)

            self.media.find(upload_date=upload_date)
            gridfs.find.assert_called_with(query_upload_date)

            self.media.find()
            gridfs.find.assert_called_with({})

    def _mock_gridfs(self):
        gridfs = Mock()
        gridfs.put = Mock(return_value='y')
        gridfs.find = Mock(return_value=[])
        self.media._fs['MONGO'] = gridfs
        return gridfs
