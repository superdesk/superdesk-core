import os
import time
from io import BytesIO

from datetime import timedelta
from unittest.mock import patch, Mock, AsyncMock

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from superdesk.storage import AmazonMediaStorage
from superdesk.media.media_operations import guess_media_extension


class AmazonMediaStorageTestCase(TestCase):
    async def test_async_upload_logs_storage_milestones(self):
        content = BytesIO(b"upload")
        with (
            patch.object(self.amazon, "_check_exists_async", new_callable=AsyncMock, return_value=False),
            patch.object(self.amazon, "call_async", new_callable=AsyncMock) as call,
            self.assertLogs("superdesk.storage.amazon_media_storage", level="INFO") as logs,
        ):
            media_id = await self.amazon.put_async(
                content, filename="upload-reference", content_type="audio/mpeg", _id="media-id"
            )
        self.assertEqual(media_id, "media-id")
        call.assert_awaited_once_with(
            "upload_fileobj",
            Fileobj=content,
            Key="media-id",
            ExtraArgs={"ContentType": "audio/mpeg", "Metadata": {"filename": "upload-reference"}},
        )
        messages = [record.getMessage() for record in logs.records]
        self.assertIn("S3 upload checking existence media=media-id upload=upload-reference", messages)
        self.assertTrue(any("S3 upload existence checked media=media-id exists=False" in msg for msg in messages))
        self.assertIn("S3 upload preparing body media=media-id", messages)
        self.assertIn("S3 upload sending body media=media-id method=upload_fileobj", messages)
        self.assertTrue(messages[-1].startswith("S3 upload completed media=media-id elapsed="))

    async def test_failed_async_upload_does_not_log_completion(self):
        with (
            patch.object(self.amazon, "_check_exists_async", new_callable=AsyncMock, return_value=False),
            patch.object(self.amazon, "call_async", new_callable=AsyncMock, side_effect=RuntimeError("S3 unavailable")),
            self.assertLogs("superdesk.storage.amazon_media_storage", level="INFO") as logs,
        ):
            with self.assertRaisesRegex(RuntimeError, "S3 unavailable"):
                await self.amazon.put_async(b"upload", content_type="audio/mpeg", _id="media-id")
        messages = [record.getMessage() for record in logs.records]
        self.assertIn("S3 upload sending body media=media-id method=put_object", messages)
        self.assertFalse(any("S3 upload completed" in msg for msg in messages))

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.amazon = AmazonMediaStorage(self.app)

        # Patch config with defaults
        p = patch.dict(
            self.app.config,
            {
                "AMAZON_SECRET_ACCESS_KEY": None,
                "AMAZON_CONTAINER_NAME": "acname",
                "AMAZON_REGION": "us-east-1",
                "AMAZON_S3_SUBFOLDER": "",
                "MEDIA_PREFIX": "https://acname.s3-us-east-1.amazonaws.com",
            },
        )
        p.start()
        self.addCleanup(p.stop)

    @patch("superdesk.storage.amazon_media_storage.ObjectId", return_value="507f1f77bcf86cd799439011")
    def test_media_url(self, _mock_object_id):
        # automatic version is set on hourly granularity.
        time_id = time.strftime("%Y%m%d%H")
        media_id = self.amazon.media_id()
        self.assertEqual(f"{time_id}/507f1f77bcf86cd799439011", media_id)
        self.assertEqual(self.amazon.url_for_media(media_id), "https://acname.s3-us-east-1.amazonaws.com/%s" % media_id)
        sub = "test-sub"
        settings = {"AMAZON_S3_SUBFOLDER": sub, "MEDIA_PREFIX": "https://acname.s3-us-east-1.amazonaws.com/" + sub}
        with patch.dict(self.app.config, settings):
            media_id = self.amazon.media_id()
            self.assertEqual(f"{time_id}/507f1f77bcf86cd799439011", media_id)
            path = "%s/%s" % (sub, media_id)
            self.assertEqual(self.amazon.url_for_media(media_id), "https://acname.s3-us-east-1.amazonaws.com/%s" % path)
            with patch.object(self.amazon, "client") as s3:
                self.amazon.get(media_id)
                self.assertTrue(s3.get_object.called)
                self.assertEqual(s3.get_object.call_args[1], dict(Bucket="acname", Key=path))

    @patch("superdesk.storage.amazon_media_storage.ObjectId", return_value="507f1f77bcf86cd799439011")
    def test_media_id_time_prefix(self, _mock_object_id):
        with patch.dict(self.app.config, {"AMAZON_MEDIA_ID_TIME_PREFIX": "none"}):
            media_id = self.amazon.media_id()
            self.assertEqual("507f1f77bcf86cd799439011", media_id)

        with patch("superdesk.storage.amazon_media_storage.time.strftime", return_value="20260102"):
            with patch.dict(self.app.config, {"AMAZON_MEDIA_ID_TIME_PREFIX": "daily"}):
                media_id = self.amazon.media_id()
                self.assertEqual("20260102/507f1f77bcf86cd799439011", media_id)

        with patch("superdesk.storage.amazon_media_storage.time.strftime", return_value="2026010215"):
            with patch.dict(self.app.config, {"AMAZON_MEDIA_ID_TIME_PREFIX": "hourly"}):
                media_id = self.amazon.media_id()
                self.assertEqual("2026010215/507f1f77bcf86cd799439011", media_id)

    def test_put_and_delete(self):
        """Test amazon if configured.

        If the environment variables have a Amazon secret key set then assume
        that we can attempt to put and delete into s3

        :return:
        """
        if self.app.config["AMAZON_SECRET_ACCESS_KEY"]:
            id = self.amazon.put("test", content_type="text/plain")
            self.assertIsNot(id, None)
            self.assertTrue(self.amazon.exists(id))
            fromS3 = self.amazon.get(id)
            self.assertEqual(fromS3.read().decode("utf-8"), "test")
            self.amazon.delete(id)
            self.assertFalse(self.amazon.exists(id))
        else:
            self.assertTrue(True)

    @patch("superdesk.storage.amazon_media_storage.ObjectId", return_value="507f1f77bcf86cd799439011")
    @patch("superdesk.storage.amazon_media_storage.time.strftime", return_value="2026010215")
    def test_put_into_folder(self, mock_time_strftime, _mock_object_id):
        data = b"test data"
        folder = "s3test"
        filename = "abc123.zip"
        content_type = "application/zip"
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)

        self.amazon.put(data, filename, content_type, folder=folder)

        kwargs = {
            "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
            "Body": data,
            "Bucket": "acname",
            "ContentType": content_type,
            "Metadata": {"filename": filename},
        }
        self.amazon.client.put_object.assert_called_once_with(**kwargs)

    def test_find_folder(self):
        self.amazon.client = Mock()

        # Mock getting list of files from Amazon, first request returns a file, second request returns empty list
        self.amazon.client.list_objects = Mock(
            side_effect=[
                {
                    "Contents": [
                        {
                            "Key": "gridtest/abcd1234",
                            "LastModified": utcnow() - timedelta(minutes=30),
                            "Size": 500,
                            "ETag": "abcd1234",
                        }
                    ]
                },
                {"Contents": []},
            ]
        )

        folder = "gridtest"
        self.amazon.find(folder=folder)

        call_arg_list = [
            ({"Bucket": "acname", "Marker": "", "MaxKeys": 1000, "Prefix": "{}/".format(folder)},),
            ({"Bucket": "acname", "Marker": "gridtest/abcd1234", "MaxKeys": 1000, "Prefix": "{}/".format(folder)},),
        ]

        # We test the call_args_list as self.amazon.client.list_objects would have been called twice
        self.assertEqual(self.amazon.client.list_objects.call_count, 2)
        self.assertEqual(self.amazon.client.list_objects.call_args_list, call_arg_list)

    def test_guess_extension(self):
        self.assertEqual(".jpg", guess_media_extension("image/jpeg"))
        self.assertEqual(".png", guess_media_extension("image/png"))

        self.assertEqual(".mp3", guess_media_extension("audio/mp3"))
        self.assertEqual(".mp3", guess_media_extension("audio/mpeg"))
        self.assertEqual(".flac", guess_media_extension("audio/flac"))

        self.assertEqual(".mp4", guess_media_extension("video/mp4"))

        # leave empty when there is no extension
        self.assertEqual("", guess_media_extension("audio/foo"))

    @patch("superdesk.storage.amazon_media_storage.ObjectId", return_value="507f1f77bcf86cd799439011")
    def test_media_url_none_utf8(self, _mock_object_id):
        filename = "[DIARY NOTE] – Victory In The Pacific Day Commemoration - Thursday (1)"
        # automatic version is set on hourly granularity.
        time_id = time.strftime("%Y%m%d%H")
        media_id = self.amazon.media_id()
        self.assertEqual(f"{time_id}/507f1f77bcf86cd799439011", media_id)
        self.assertEqual(self.amazon.url_for_media(media_id), "https://acname.s3-us-east-1.amazonaws.com/%s" % media_id)
        sub = "test-sub"
        settings = {"AMAZON_S3_SUBFOLDER": sub, "MEDIA_PREFIX": "https://acname.s3-us-east-1.amazonaws.com/" + sub}
        with patch.dict(self.app.config, settings):
            media_id = self.amazon.media_id()
            self.assertEqual(f"{time_id}/507f1f77bcf86cd799439011", media_id)
            path = "%s/%s" % (sub, media_id)
            self.assertEqual(self.amazon.url_for_media(media_id), "https://acname.s3-us-east-1.amazonaws.com/%s" % path)
            with patch.object(self.amazon, "client") as s3:
                self.amazon.get(media_id)
                self.assertTrue(s3.get_object.called)
                self.assertEqual(s3.get_object.call_args[1], dict(Bucket="acname", Key=path))

    @patch("superdesk.storage.amazon_media_storage.ObjectId", return_value="507f1f77bcf86cd799439011")
    def test_put_into_folder_none_utf8(self, _mock_object_id):
        data = b"test data"
        folder = "s3test"
        filename = "[DIARY NOTE] – Victory In The Pacific Day Commemoration - Thursday (1).pdf"
        content_type = "application/pdf"
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)

        self.amazon.put(data, filename, content_type, folder=folder, version=False)

        kwargs = {
            "Key": f"{folder}/507f1f77bcf86cd799439011",
            "Body": data,
            "Bucket": "acname",
            "ContentType": content_type,
            "Metadata": {"filename": "DIARY NOTE - Victory In The Pacific Day Commemoration - Thursday (1).pdf"},
        }
        self.amazon.client.put_object.assert_called_once_with(**kwargs)

    def test_get_none_utf8(self):
        self.amazon.client.get_object = Mock()
        self.amazon.extract_metadata_from_headers = Mock(return_value={})

        self.amazon.get("[DIARY NOTE] – Victory In The Pacific Day Commemoration - Thursday (1).pdf")

        kwargs = {"Bucket": "acname", "Key": "DIARY NOTE - Victory In The Pacific Day Commemoration - Thursday (1).pdf"}
        self.amazon.client.get_object.assert_called_once_with(**kwargs)

    @patch("superdesk.storage.amazon_media_storage.ObjectId", return_value="507f1f77bcf86cd799439011")
    @patch("superdesk.storage.amazon_media_storage.time.strftime", return_value="2026010215")
    def test_mimetype_detect(self, mock_time_strftime, _mock_object_id):
        # keep default mimetype
        content = b"bytes are here"
        filename = "extensionless"
        content_type = "text/css"
        folder = "f1"
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)
        self.amazon.put(content, filename, content_type, folder=folder)
        self.amazon.client.put_object.assert_called_once_with(
            **{
                "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                "Body": content,
                "Bucket": "acname",
                "ContentType": content_type,
                "Metadata": {"filename": filename},
            }
        )

        # get mimetype from the filename
        content = b"bytes are here"
        filename = "styles.css"
        content_type = "application/pdf"
        folder = "f1"
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)
        self.amazon.put(content, filename, content_type, folder=folder)
        self.amazon.client.put_object.assert_called_once_with(
            **{
                "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                "Body": b"bytes are here",
                "Bucket": "acname",
                "ContentType": "text/css",
                "Metadata": {"filename": filename},
            }
        )

        content = b"bytes are here"
        filename = "styles.JpG"
        content_type = "application/pdf"
        folder = "f1"
        self.amazon.client.put_object = Mock()
        self.amazon._check_exists = Mock(return_value=False)
        self.amazon.put(content, filename, content_type, folder=folder)
        self.amazon.client.put_object.assert_called_once_with(
            **{
                "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                "Body": b"bytes are here",
                "Bucket": "acname",
                "ContentType": "image/jpeg",
                "Metadata": {"filename": filename},
            }
        )

        # get mimetype from the file
        fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures")

        with open(os.path.join(fixtures_path, "file_example-jpg.jpg"), "rb") as content:
            filename = "extensionless"
            content_type = "dummy/text"
            folder = "f1"
            self.amazon.client.put_object = Mock()
            self.amazon._check_exists = Mock(return_value=False)
            self.amazon.put(content, filename, content_type, folder=folder)
            self.amazon.client.put_object.assert_called_once_with(
                **{
                    "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                    "Body": content,
                    "Bucket": "acname",
                    "ContentType": "image/jpeg",
                    "Metadata": {"filename": filename},
                }
            )

            with open(os.path.join(fixtures_path, "file_example-xls.xls"), "rb") as content:
                filename = "extensionless"
                content_type = "dummy/text"
                folder = "f1"
                self.amazon.client.put_object = Mock()
                self.amazon._check_exists = Mock(return_value=False)
                self.amazon.put(content, filename, content_type, folder=folder)
                self.amazon.client.put_object.assert_called_once_with(
                    **{
                        "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                        "Body": content,
                        "Bucket": "acname",
                        "ContentType": "application/vnd.ms-excel",
                        "Metadata": {"filename": filename},
                    }
                )

            with open(os.path.join(fixtures_path, "file_example-xlsx.xlsx"), "rb") as content:
                filename = "extensionless"
                content_type = "dummy/text"
                folder = "f1"
                self.amazon.client.put_object = Mock()
                self.amazon._check_exists = Mock(return_value=False)
                self.amazon.put(content, filename, content_type, folder=folder)
                self.amazon.client.put_object.assert_called_once_with(
                    **{
                        "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                        "Body": content,
                        "Bucket": "acname",
                        "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "Metadata": {"filename": filename},
                    }
                )

            with open(os.path.join(fixtures_path, "file_example-docx.docx"), "rb") as content:
                filename = "extensionless"
                content_type = "dummy/text"
                folder = "f1"
                self.amazon.client.put_object = Mock()
                self.amazon._check_exists = Mock(return_value=False)
                self.amazon.put(content, filename, content_type, folder=folder)
                self.amazon.client.put_object.assert_called_once_with(
                    **{
                        "Key": f"{folder}/2026010215/507f1f77bcf86cd799439011",
                        "Body": content,
                        "Bucket": "acname",
                        "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "Metadata": {"filename": filename},
                    }
                )
