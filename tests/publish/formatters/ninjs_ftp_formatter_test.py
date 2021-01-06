# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
from unittest import mock
from datetime import timedelta

from superdesk.tests import TestCase
from superdesk.publish.formatters.ninjs_ftp_formatter import FTPNinjsFormatter
from superdesk.publish import init_app
from superdesk.utc import utcnow


@mock.patch("superdesk.publish.subscribers.SubscribersService.generate_sequence_number", lambda self, subscriber: 1)
class FTPNinjsFormatterTest(TestCase):
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
                    "media": "12345/5e448dd1016d1f63a92f0398.jpg",
                },
                "custom": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158637458/Original/download",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg",
                },
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
        seq, doc = self.formatter.format(
            article,
            {
                "name": "Test Subscriber",
                "destinations": [
                    {
                        "config": {
                            "host": "ftp.abc.com",
                            "path": "/stories",
                            "associated_path": "/pictures",
                            "push_associated": True,
                        }
                    }
                ],
            },
        )[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "custom": {
                    "href": "/pictures/12345-5e448dd1016d1f63a92f0400.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg",
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
        self.assertNotIn("viewImage", json.loads(doc).get("renditions"))

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
                    "media": "12345/5e448dd1016d1f63a92f0398.jpg",
                },
                "custom": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158637458/Original/download",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg",
                },
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
        seq, doc = self.formatter.format(
            article,
            {
                "name": "Test Subscriber",
                "destinations": [
                    {
                        "config": {
                            "host": "ftp.abc.com",
                            "path": "/stories",
                            "associated_path": "/pictures",
                            "push_associated": True,
                            "include_original": True,
                        }
                    }
                ],
            },
        )[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "custom": {
                    "href": "/pictures/12345-5e448dd1016d1f63a92f0400.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg",
                },
                "original": {
                    "href": "/pictures/12345-5e448dd1016d1f63a92f0398.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0398.jpg",
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
        self.assertNotIn("viewImage", json.loads(doc).get("renditions"))

    def test_embedded_image(self):
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
            "_id": "urn:newsml:localhost:2020-03-12T15:19:39.654956:e78f3dd6-c096-43d5-9ba0-014e07dc4f1f",
            "target_regions": [],
            "priority": 6,
            "place": [
                {
                    "world_region": "Asia",
                    "name": "ASIA",
                    "country": "",
                    "qcode": "ASIA",
                    "group": "Rest Of World",
                    "state": "",
                }
            ],
            "associations": {
                "editor_0": {
                    "_current_version": 1,
                    "byline": "Some One",
                    "_latest_version": 1,
                    "family_id": "20181226001377597230",
                    "type": "picture",
                    "unique_id": 35167342,
                    "_id": "tag:localhost:2019:5c9da5e1-f491-4ffd-a0b5-dd54e9fd870f",
                    "versioncreated": "2019-04-05T05:37:44+0000",
                    "alt_text": "Power plant",
                    "archive_description": "Steam rises from the brown coal-fired power plant",
                    "format": "HTML",
                    "pubstatus": "usable",
                    "mimetype": "image/jpeg",
                    "description_text": "Steam rises from the brown coal-fired power plant",
                    "firstcreated": "2018-12-04T15:17:37+0000",
                    "renditions": {
                        "original": {
                            "mimetype": "image/jpeg",
                            "href": "http://superdesk-uat.aap.com.au/api/upload-raw/20190405160436/9e0b3096a5792b1e6"
                            "46a6b1e7dad606ccc697b4b686dde76b13b7b64e994f579.jpg",
                            "width": 4500,
                            "height": 3000,
                            "poi": {"y": 1770, "x": 2160},
                            "media": "20190405160436/9e0b3096a5792b1e646a6b1e7dad606ccc"
                            "697b4b686dde76b13b7b64e994f579.jpg",
                        }
                    },
                    "language": "en",
                    "state": "fetched",
                    "_links": {
                        "collection": {"title": "archive", "href": "archive"},
                        "parent": {"title": "home", "href": "/"},
                        "self": {
                            "title": "Archive",
                            "href": "archive/tag:localhost:2019:5c9da5e1-f491-4ffd-a0b5-dd54e9fd870f",
                        },
                    },
                    "_etag": "16d959004ace3137f977650b52ba1db74ca4058b",
                    "source": "XXX",
                    "ingest_id": "20181226001377597230",
                    "original_source": "XXX/XXX",
                    "priority": 6,
                    "operation": "fetch",
                    "sign_off": "MD",
                    "version_creator": "5673a749069b7f6e7ff8de6c",
                    "guid": "20181226001377597230",
                    "expiry": "2019-04-08T05:37:45+0000",
                    "headline": "YEARENDER DECEMBER 2018",
                    "original_creator": "5673a749069b7f6e7ff8de6c",
                    "urgency": 3,
                    "slugline": "YEARENDER DECEMBER 2018",
                    "genre": [{"qcode": "Article", "name": "Article"}],
                    "poi": {"y": 0.59, "x": 0.48},
                }
            },
            "family_id": "urn:newsml:localhost:2020-03-12T15:19:39.654956:e78f3dd6-c096-43d5-9ba0-014e07dc4f1f",
            "keywords": [],
            "genre": [{"qcode": "Article", "name": "Article", "scheme": None}],
            "format": "HTML",
            "unique_id": 37642265,
            "operation": "update",
            "type": "text",
            "description_text": "",
            "headline": "Test Headline",
            "urgency": 3,
            "unique_name": "#37642265",
            "anpa_category": [{"qcode": "a", "name": "Australian General News"}],
            "version": 1,
            "byline": "Fred Flinstone",
            "target_subscribers": [],
            "slugline": "Test",
            "subject": [{"qcode": "01001000", "name": "archaeology", "parent": "01000000"}],
            "language": "en",
            "body_html": '<p>Some text</p>\n<!-- EMBED START Image {id: "editor_0"} -->\n<figure>\n    '
            '<img src="http://superdesk-uat.aap.com.au/api/upload-raw/20190405160436/9e0b3096a5792b1'
            'e646a6b1e7dad606ccc697b4b686dde76b13b7b64e994f579.jpg" alt="Power plant" />\n    '
            "<figcaption>Steam rises from the brown coal-fired power plant</figcaption>\n</figure>\n"
            '<!-- EMBED END Image {id: "editor_0"} -->\n<p>More text</p>',
            "source": "aap",
            "body_footer": "",
            "guid": "urn:newsml:localhost:2020-03-12T15:19:39.654956:e78f3dd6-c096-43d5-9ba0-014e07dc4f1f",
        }
        seq, doc = self.formatter.format(
            article,
            {
                "name": "Test Subscriber",
                "destinations": [
                    {
                        "config": {
                            "host": "ftp.abc.com",
                            "path": "/stories",
                            "associated_path": "/pictures",
                            "push_associated": True,
                            "include_original": True,
                        }
                    }
                ],
            },
        )[0]
        expected = {
            "source": "aap",
            "readtime": 0,
            "headline": "Test Headline",
            "keywords": [],
            "associations": {
                "editor_0": {
                    "source": "XXX",
                    "headline": "YEARENDER DECEMBER 2018",
                    "firstcreated": "2018-12-04T15:17:37+0000",
                    "guid": "20181226001377597230",
                    "type": "picture",
                    "byline": "Some One",
                    "urgency": 3,
                    "language": "en",
                    "slugline": "YEARENDER DECEMBER 2018",
                    "versioncreated": "2019-04-05T05:37:44+0000",
                    "mimetype": "image/jpeg",
                    "genre": [{"name": "Article", "code": "Article"}],
                    "priority": 6,
                    "renditions": {
                        "original": {
                            "mimetype": "image/jpeg",
                            "poi": {"x": 2160, "y": 1770},
                            "height": 3000,
                            "media": "20190405160436/9e0b3096a5792b1e646a6b1e7dad606ccc697b4b686"
                            "dde76b13b7b64e994f579.jpg",
                            "width": 4500,
                            "href": "/pictures/20190405160436-9e0b3096a5792b1e646a6b1e7dad606ccc69"
                            "7b4b686dde76b13b7b64e994f579.jpg",
                        }
                    },
                    "description_text": "Steam rises from the brown coal-fired power plant",
                    "pubstatus": "usable",
                    "version": "1",
                    "body_text": "Power plant",
                }
            },
            "subject": [{"name": "archaeology", "code": "01001000"}],
            "guid": "urn:newsml:localhost:2020-03-12T15:19:39.654956:e78f3dd6-c096-43d5-9ba0-014e07dc4f1f",
            "slugline": "Test",
            "charcount": 67,
            "type": "text",
            "urgency": 3,
            "language": "en",
            "byline": "Fred Flinstone",
            "wordcount": 12,
            "genre": [{"name": "Article", "code": "Article"}],
            "priority": 6,
            "place": [{"name": "ASIA", "code": "ASIA"}],
            "body_html": '<p>Some text</p>\n<!-- EMBED START Image {id: "editor_0"} -->\n<figure>\n   '
            ' <img src="/pictures/20190405160436-9e0b3096a5792b1e646a6b1e7dad606ccc697b4b686dde76b13'
            'b7b64e994f579.jpg" alt="Power plant" id="editor_0">\n    <figcaption>Steam rises from the'
            ' brown coal-fired power plant</figcaption>\n</figure>\n<!-- EMBED END Image {id: "editor_0"}'
            " -->\n<p>More text</p>",
            "service": [{"name": "Australian General News", "code": "a"}],
            "version": "1",
        }
        self.assertEqual(expected, json.loads(doc))
