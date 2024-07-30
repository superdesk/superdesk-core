import io
import unittest
import requests_mock

from superdesk.flask import Flask
from superdesk.media.media_operations import download_file_from_url


class MediaOperationsTestCase(unittest.TestCase):
    def test_download_file_from_url_relative(self):
        app = Flask(__name__)
        app.config["SERVER_NAME"] = "localhost"
        body = io.BytesIO(b"data")
        with app.app_context():
            with requests_mock.mock() as mock:
                mock.get("http://localhost/test/foo.jpg", body=body)
                out = download_file_from_url("/test/foo.jpg")
        self.assertEqual(b"data", out[0].read())
