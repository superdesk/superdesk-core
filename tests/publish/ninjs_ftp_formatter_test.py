# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from unittest import mock
from superdesk.publish.formatters.ninjs_ftp_formatter import FTPNinjsFormatter
from superdesk.publish import init_app
from superdesk.utc import utcnow
from datetime import timedelta
import json


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class NitfFormatterTest(TestCase):
    def setUp(self):
        self.formatter = FTPNinjsFormatter()
        init_app(self.app)
        self.maxDiff = None

    def test_picture_formatter(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "crop_sizes",
                    "items": [
                        {"is_active": True, "name": "custom", "width": 10000, "height": 10000},
                    ],
                }
            ],
        )

        embargoed = utcnow() + timedelta(days=2)
        article = {
            "guid": "20150723001158606583",
            "_current_version": 1,
            "slugline": "AMAZING PICTURE",
            "original_source": "AAP",
            "renditions": {
                "viewImage": {
                    "width": 640,
                    "href": "http://localhost:5000/api/upload/55b032041d41c8d278d21b6f/raw?_schema=http",
                    "mimetype": "image/jpeg",
                    "height": 401,
                },
                "original": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0398.jpg"
                },
                "custom": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158637458/Original/download",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg"
                }
            },
            "byline": "MICKEY MOUSE",
            "headline": "AMAZING PICTURE",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "ednote": "TEST ONLY",
            "type": "picture",
            "pubstatus": "usable",
            "source": "AAP",
            "description": "The most amazing picture you will ever see",
            "guid": "20150723001158606583",
            "body_footer": "<p>call helpline 999 if you are planning to quit smoking</p>",
            "embargoed": embargoed,
        }
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber", "destinations":
                                                   [{"config": {"host": "ftp.abc.com", "path": "/stories",
                                                                "associated_path": "/pictures",
                                                                "push_associated": True}}]})[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "custom": {
                    "href": "/pictures/12345-5e448dd1016d1f63a92f0400.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg"
                },
            },
            "headline": "AMAZING PICTURE",
            "pubstatus": "usable",
            "version": "1",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "guid": "20150723001158606583",
            "description_html": "The most amazing picture you will ever see<p>call helpline 999 if you are planning to "
                                "quit smoking</p>",
            "type": "picture",
            "priority": 5,
            "slugline": "AMAZING PICTURE",
            "ednote": "TEST ONLY",
            "source": "AAP",
            "embargoed": embargoed.isoformat(),
        }
        self.assertEqual(expected, json.loads(doc))
        self.assertNotIn('viewImage', json.loads(doc).get('renditions'))

    def test_picture_formatter_with_original(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "crop_sizes",
                    "items": [
                        {"is_active": True, "name": "custom", "width": 10000, "height": 10000},
                    ],
                }
            ],
        )

        embargoed = utcnow() + timedelta(days=2)
        article = {
            "guid": "20150723001158606583",
            "_current_version": 1,
            "slugline": "AMAZING PICTURE",
            "original_source": "AAP",
            "renditions": {
                "viewImage": {
                    "width": 640,
                    "href": "http://localhost:5000/api/upload/55b032041d41c8d278d21b6f/raw?_schema=http",
                    "mimetype": "image/jpeg",
                    "height": 401,
                },
                "original": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0398.jpg"
                },
                "custom": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158637458/Original/download",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg"
                }
            },
            "byline": "MICKEY MOUSE",
            "headline": "AMAZING PICTURE",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "ednote": "TEST ONLY",
            "type": "picture",
            "pubstatus": "usable",
            "source": "AAP",
            "description": "The most amazing picture you will ever see",
            "guid": "20150723001158606583",
            "body_footer": "<p>call helpline 999 if you are planning to quit smoking</p>",
            "embargoed": embargoed,
        }
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber", "destinations":
                                                   [{"config": {"host": "ftp.abc.com", "path": "/stories",
                                                    "associated_path": "/pictures",
                                                     "push_associated": True, "include_original": True}}]})[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "custom": {
                    "href": "/pictures/12345-5e448dd1016d1f63a92f0400.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg"
                },
                "original": {
                    "href": "/pictures/12345-5e448dd1016d1f63a92f0398.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0398.jpg"
                },
            },
            "headline": "AMAZING PICTURE",
            "pubstatus": "usable",
            "version": "1",
            "versioncreated": "2015-07-23T00:15:00.000Z",
            "guid": "20150723001158606583",
            "description_html": "The most amazing picture you will ever see<p>call helpline 999 if you are planning to "
                                "quit smoking</p>",
            "type": "picture",
            "priority": 5,
            "slugline": "AMAZING PICTURE",
            "ednote": "TEST ONLY",
            "source": "AAP",
            "embargoed": embargoed.isoformat(),
        }
        self.assertEqual(expected, json.loads(doc))
        self.assertNotIn('viewImage', json.loads(doc).get('renditions'))
