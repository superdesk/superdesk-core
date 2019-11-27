# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from io import BytesIO
from unittest.mock import MagicMock

import requests_mock
from werkzeug.datastructures import FileStorage

import superdesk
from superdesk import config
from superdesk.tests import TestCase


class Req(dict):
    args = {}


video_info = {
    '_id': 'video_id',
}


class VideoEditTestCase(TestCase):
    def setUp(self):
        self.video_edit = superdesk.get_resource_service('video_edit')
        self.app.config['VIDEO_SERVER_ENABLE'] = 'true'
        self.app.config['VIDEO_SERVER_URL'] = 'http://localhost'
        superdesk.Service.find_one = MagicMock()
        superdesk.Service.find_one.return_value = {'media': 'video_id'}

    def test_get_video(self):
        with requests_mock.mock() as mock:
            mock.get('http://localhost/projects/video_id', json=video_info)
            res = self.video_edit.find_one(Req())
            self.assertEqual(res['project']['_id'], video_info['_id'])

    def test_edit_video(self):
        pass

    def test_capture_thumbnail(self):
        pass

    def test_upload_thumbnail(self):
        thumbnail = {
            "mimetype": "image/jpeg",
            "url": "http://localhost/projects/video_id/raw/thumbnails/preview"
        }
        with requests_mock.mock() as mock:
            mock.post('http://localhost/projects/video_id/thumbnails', json=thumbnail)
            req = {'file': FileStorage(BytesIO(b'abcdef'), 'image.jpeg')}
            res = self.video_edit.on_replace(req, {'project': {'_id': 'video_id'}})
            self.assertEqual(
                res['renditions']['thumbnail']['href'],
                'http://localhost/projects/video_id/raw/thumbnails/preview'
            )
            self.assertEqual(res['renditions']['thumbnail']['mimetype'], 'image/jpeg')

    def test_capture_timeline(self):
        with requests_mock.mock() as mock:
            mock.get(
                'http://localhost/projects/video_id/thumbnails?type=timeline&amount=40',
                json={'processing': True},
                status_code=202,
            )
            req = Req()
            setattr(req, 'args', {'action': 'timeline'})
            res = self.video_edit.find_one(req)
            self.assertEqual(res[config.ID_FIELD], video_info['_id'])
            self.assertTrue(res['processing'])
