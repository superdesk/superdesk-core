# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import copy
from io import BytesIO
from unittest.mock import MagicMock

import magic
import requests_mock
from werkzeug.datastructures import FileStorage

import superdesk
from superdesk import config
from superdesk.errors import SuperdeskApiError
from superdesk.tests import TestCase


class Req(dict):
    args = {}


video_info = {
    "_id": "video_id",
}


class VideoEditTestCase(TestCase):
    project_data = {
        "_id": "video_id",
        "metadata": {
            "codec_name": "h264",
            "width": 1280,
            "height": 720,
            "duration": 10,
        },
        "url": "video_url",
        "mime_type": "video/mp4",
        "version": 1,
    }

    def setUp(self):
        self.video_edit = superdesk.get_resource_service("video_edit")
        self.app.config["VIDEO_SERVER_ENABLED"] = "true"
        self.app.config["VIDEO_SERVER_URL"] = "http://localhost"
        with requests_mock.mock() as mock:
            dirname = os.path.dirname(os.path.realpath(__file__))
            video_file_path = os.path.normpath(os.path.join(dirname, "fixtures", "envy_dog.mp4"))

            with open(video_file_path, "rb") as f:
                doc = {"media": FileStorage(BytesIO(f.read()), "video.mp4", content_type="video/mp4")}

            mock.post("http://localhost/projects/", json=self.project_data)
            mock.get("http://localhost/projects/video_id/thumbnails?type=timeline&amount=60", json={"processing": True})
            archive_service = superdesk.get_resource_service("archive")
            magic.from_buffer = MagicMock()
            magic.from_buffer.return_value = "video/mp4"
            self.item = archive_service.find_one(req=None, _id=archive_service.post([doc])[0])

    def test_get_video(self):
        with requests_mock.mock() as mock:
            mock.get("http://localhost/projects/video_id", json=video_info)
            res = self.video_edit.find_one(Req(), _id=self.item["_id"])
            self.assertEqual(res["project"]["_id"], video_info["_id"])

    def test_upload_video(self):
        self.assertEqual(
            self.item["renditions"],
            {"original": {"href": "video_url", "mimetype": "video/mp4", "version": 1, "video_editor_id": "video_id"}},
        )

    def test_missing_video_id(self):
        doc = {"item": {config.ID_FIELD: "123", "renditions": {"original": {}}}}
        with self.assertRaises(SuperdeskApiError) as ex:
            self.video_edit.create([doc])
        self.assertEqual(ex.exception.message, '"video_editor_id" is required')

    def test_missing_action(self):
        doc = {"item": {config.ID_FIELD: "123", "renditions": {"original": {"video_editor_id": "video_id"}}}}
        with self.assertRaises(SuperdeskApiError) as ex:
            self.video_edit.create([doc])
        self.assertEqual(ex.exception.message, '"capture" or "edit" is required')

    def test_edit_video(self):
        project_data = copy.deepcopy(self.project_data)
        doc = {
            "item": {
                config.ID_FIELD: self.item[config.ID_FIELD],
                "renditions": self.item["renditions"],
            },
            "edit": {"crop": "0,0,200,500", "rotate": -90, "trim": "5,15"},
        }
        with requests_mock.mock() as mock:
            project_data["version"] = 2
            mock.get("http://localhost/projects/video_id", json=project_data)
            mock.post("http://localhost/projects/video_id/duplicate", json=project_data)
            mock.put("http://localhost/projects/video_id", json={"processing": True})
            item = self.video_edit.find_one(req=None, _id=self.video_edit.create([doc])[0])
            self.assertEqual(
                item["renditions"],
                {
                    "original": {
                        "href": "video_url",
                        "mimetype": "video/mp4",
                        "version": 3,
                        "video_editor_id": "video_id",
                    }
                },
            )

    def test_capture_thumbnail(self):
        doc = {
            "item": {
                config.ID_FIELD: self.item[config.ID_FIELD],
                "renditions": self.item["renditions"],
            },
            "capture": {"crop": "0,0,200,500", "rotate": -90, "trim": "5,10"},
        }
        project_data = copy.deepcopy(self.project_data)
        project_data.setdefault("thumbnails", {})["preview"] = {
            "mimetype": "image/png",
            "url": "http://localhost/projects/video_id/raw/thumbnails/preview",
        }
        with requests_mock.mock() as mock:
            mock.get("http://localhost/projects/video_id", json=project_data)
            mock.post("http://localhost/projects/video_id", json={"processing": True})
            mock.get(
                "http://localhost/projects/video_id/thumbnails?type=preview&crop=0,0,200,500&rotate=-90",
                json=project_data,
            )
            item = self.video_edit.find_one(req=None, _id=self.video_edit.create([doc])[0])
            self.assertEqual(
                item["renditions"],
                {
                    "original": {
                        "href": "video_url",
                        "mimetype": "video/mp4",
                        "version": 1,
                        "video_editor_id": "video_id",
                    },
                    "viewImage": {
                        "mimetype": "image/png",
                        "href": "http://localhost/projects/video_id/raw/thumbnails/preview",
                    },
                },
            )

    def test_upload_thumbnail(self):
        thumbnail = {"mimetype": "image/jpeg", "url": "http://localhost/projects/video_id/raw/thumbnails/preview"}
        with requests_mock.mock() as mock:
            mock.post("http://localhost/projects/video_id/thumbnails", json=thumbnail)
            req = {"file": FileStorage(BytesIO(b"abcdef"), "image.jpeg")}
            res = self.video_edit.on_replace(req, {"project": {"_id": "video_id"}})
            self.assertEqual(
                res["renditions"]["viewImage"]["href"], "http://localhost/projects/video_id/raw/thumbnails/preview"
            )
            self.assertEqual(res["renditions"]["viewImage"]["mimetype"], "image/jpeg")

    def test_capture_timeline(self):
        with requests_mock.mock() as mock:
            mock.get(
                "http://localhost/projects/video_id/thumbnails?type=timeline&amount=60",
                json={"processing": True},
                status_code=202,
            )
            req = Req()
            setattr(req, "args", {"action": "timeline"})
            res = self.video_edit.find_one(req, _id=self.item["_id"])
            self.assertEqual(res[config.ID_FIELD], video_info["_id"])
            self.assertTrue(res["processing"])
