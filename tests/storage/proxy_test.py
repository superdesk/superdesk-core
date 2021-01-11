import io
import bson
import flask
import unittest

from unittest.mock import create_autospec, patch
from superdesk.storage.proxy import ProxyMediaStorage
from superdesk.storage.desk_media_storage import SuperdeskGridFSMediaStorage
from superdesk.storage.amazon_media_storage import AmazonMediaStorage


class SuperdeskMediaStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.config.update(
            dict(
                AMAZON_ACCESS_KEY_ID="foo",
                AMAZON_SECRET_ACCESS_KEY="bar",
                AMAZON_ENDPOINT_URL="http://example.com",
            )
        )
        self.storage = ProxyMediaStorage(self.app)
        self.storage._storage = [
            create_autospec(SuperdeskGridFSMediaStorage),
            create_autospec(AmazonMediaStorage),
        ]

    def test_storage(self):
        content = io.BytesIO(b"foo")
        _media = {"_id": "test"}

        self.storage._storage[0].exists.return_value = False
        self.storage._storage[0].get_by_filename.return_value = "mongo"

        self.storage._storage[1].exists.return_value = True
        self.storage._storage[1].get.return_value = _media
        self.storage._storage[1].url_for_media.return_value = "url_for_media"
        self.storage._storage[1].url_for_download.return_value = "url_for_download"

        self.storage._storage[0].put.return_value = "media_id"
        _id = self.storage.put(content, "filename", "text/plain", "test")
        self.storage._storage[0].put.assert_called_once_with(
            content, filename="filename", content_type="text/plain", metadata="test", resource=None
        )

        self.assertIsNotNone(self.storage.get(_id))

        self.storage.delete(_id)
        self.storage._storage[1].delete.assert_called_once_with(_id, None)

        self.assertEqual(_media, self.storage.fetch_rendition({"media": "foo"}))

        self.assertEqual("url_for_media", self.storage.url_for_media("test"))
        self.assertEqual("url_for_download", self.storage.url_for_download("test"))

        self.assertEqual("mongo", self.storage.get_by_filename("path"))

    def test_amazon_get_by_filename_mongo(self):
        _id = bson.ObjectId()
        amazon = AmazonMediaStorage(self.app)
        with patch.object(amazon, "get") as get_mock:
            amazon.get_by_filename("{}.jpg".format(str(_id)))
            get_mock.assert_called_once_with(str(_id))
