import os
import io
import bson
from unittest.mock import Mock, ANY

from superdesk.upload import upload_url
from superdesk.utc import utcnow
from superdesk.utils import sha
from superdesk.tests import AsyncFlaskTestCase
from datetime import timedelta


class GridFSMediaStorageTestCase(AsyncFlaskTestCase):
    app_config = {
        "MEDIA_PREFIX": "http://localhost/upload-raw",
        "DOMAIN": {"upload": {}},
        "MONGO_DBNAME": "sptests",
        "MEDIA_STORAGE_PROVIDER": "superdesk.storage.SuperdeskGridFSMediaStorage",
    }

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.upload_url = upload_url

    async def test_url_for_media(self):
        _id = bson.ObjectId(sha("test")[:24])
        url = self.app.media.url_for_media(_id)
        self.assertEqual("http://localhost/upload-raw/%s" % _id, url)

    async def test_url_for_media_content_type(self):
        _id_str = "1" * 24
        _id = bson.ObjectId(_id_str)
        url = self.app.media.url_for_media(_id, "image/jpeg")
        self.assertEqual("http://localhost/upload-raw/{}.jpg".format(_id_str), url)

    async def test_put_media_with_id(self):
        data = io.StringIO("test data")
        filename = "x"

        gridfs = self._mock_gridfs()
        _id = bson.ObjectId()

        self.app.media.put(data, filename=filename, content_type="text/plain", _id=str(_id))

        kwargs = {
            "content_type": "text/plain",
            "filename": filename,
            "metadata": {
                "md5": ANY,
                "content_type": '"text/plain"',
            },
            "_id": _id,
            "md5": ANY,
        }

        gridfs.put.assert_called_once_with(data, **kwargs)

    async def test_put_into_folder(self):
        data = b"test data"
        filename = "x"
        folder = "gridtest"

        gridfs = self._mock_gridfs()

        self.app.media.put(data, filename=filename, content_type="text/plain", folder=folder)

        kwargs = {
            "content_type": "text/plain",
            "filename": "{}/{}".format(folder, filename),
            "metadata": {
                "md5": ANY,
                "content_type": '"text/plain"',
            },
            "md5": ANY,
        }

        gridfs.put.assert_called_once_with(data, **kwargs)

    async def test_find_files(self):
        gridfs = self._mock_gridfs()
        upload_date = {"$lte": utcnow(), "$gte": utcnow() - timedelta(hours=1)}
        folder = "gridtest"
        query_filename = {"filename": {"$regex": "^{}/".format(folder)}}
        query_upload_date = {"uploadDate": upload_date}

        self.app.media.find(folder=folder, upload_date=upload_date)
        gridfs.find.assert_called_once_with({"$and": [query_filename, query_upload_date]})

        self.app.media.find(folder=folder)
        gridfs.find.assert_called_with(query_filename)

        self.app.media.find(upload_date=upload_date)
        gridfs.find.assert_called_with(query_upload_date)

        self.app.media.find()
        gridfs.find.assert_called_with({})

    async def test_custom_id(self):
        data = b"foo"
        self.app.media.put(data, _id="foo")
        _file = self.app.media.get("foo")
        assert data == _file.read()

    def _mock_gridfs(self):
        gridfs = Mock()
        gridfs.put = Mock(return_value="y")
        gridfs.find = Mock(return_value=[])
        self.app.media._fs["MONGO"] = gridfs
        return gridfs

    async def test_mimetype_detect(self):
        # keep default mimetype
        gridfs = self._mock_gridfs()
        _id = bson.ObjectId()
        content = b"bytes are here"
        filename = "extensionless"
        content_type = "text/css"
        self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
        kwargs = {
            "content_type": content_type,
            "filename": filename,
            "metadata": {
                "md5": ANY,
                "content_type": f'"{content_type}"',
            },
            "_id": _id,
            "md5": ANY,
        }
        gridfs.put.assert_called_once_with(content, **kwargs)

        # get mimetype from the filename
        gridfs = self._mock_gridfs()
        _id = bson.ObjectId()
        content = b"bytes are here"
        filename = "styles.css"
        content_type = "application/pdf"
        self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
        kwargs = {
            "content_type": "text/css",
            "filename": filename,
            "metadata": {
                "md5": ANY,
                "content_type": '"text/css"',
            },
            "_id": _id,
            "md5": ANY,
        }
        gridfs.put.assert_called_once_with(content, **kwargs)

        gridfs = self._mock_gridfs()
        _id = bson.ObjectId()
        content = b"bytes are here"
        filename = "styles.JpG"
        content_type = "application/pdf"
        self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
        kwargs = {
            "content_type": "image/jpeg",
            "filename": filename,
            "metadata": {
                "md5": ANY,
                "content_type": '"image/jpeg"',
            },
            "_id": _id,
            "md5": ANY,
        }
        gridfs.put.assert_called_once_with(content, **kwargs)

        # get mimetype from the file
        fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures")
        with open(os.path.join(fixtures_path, "file_example-jpg.jpg"), "rb") as content:
            gridfs = self._mock_gridfs()
            _id = bson.ObjectId()
            filename = "extensionless"
            content_type = "dummy/text"
            self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
            kwargs = {
                "content_type": "image/jpeg",
                "filename": filename,
                "metadata": {
                    "md5": ANY,
                    "content_type": '"image/jpeg"',
                },
                "_id": _id,
                "md5": ANY,
            }
            gridfs.put.assert_called_once_with(content, **kwargs)

        with open(os.path.join(fixtures_path, "file_example-xls.xls"), "rb") as content:
            gridfs = self._mock_gridfs()
            _id = bson.ObjectId()
            filename = "extensionless"
            content_type = "dummy/text"
            self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
            kwargs = {
                "content_type": "application/vnd.ms-excel",
                "filename": filename,
                "metadata": {
                    "md5": ANY,
                    "content_type": '"application/vnd.ms-excel"',
                },
                "_id": _id,
                "md5": ANY,
            }
            gridfs.put.assert_called_once_with(content, **kwargs)

        with open(os.path.join(fixtures_path, "file_example-xlsx.xlsx"), "rb") as content:
            gridfs = self._mock_gridfs()
            _id = bson.ObjectId()
            filename = "extensionless"
            content_type = "dummy/text"
            self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
            kwargs = {
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "filename": filename,
                "metadata": {
                    "md5": ANY,
                    "content_type": '"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"',
                },
                "_id": _id,
                "md5": ANY,
            }
            gridfs.put.assert_called_once_with(content, **kwargs)

        with open(os.path.join(fixtures_path, "file_example-docx.docx"), "rb") as content:
            gridfs = self._mock_gridfs()
            _id = bson.ObjectId()
            filename = "extensionless"
            content_type = "dummy/text"
            self.app.media.put(content, filename=filename, content_type=content_type, _id=str(_id))
            kwargs = {
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "filename": filename,
                "metadata": {
                    "md5": ANY,
                    "content_type": '"application/vnd.openxmlformats-officedocument.wordprocessingml.document"',
                },
                "_id": _id,
                "md5": ANY,
            }
            gridfs.put.assert_called_once_with(content, **kwargs)
