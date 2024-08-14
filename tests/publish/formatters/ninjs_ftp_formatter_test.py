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
from superdesk.editor_utils import Editor3Content
from superdesk.publish import init_app
from superdesk.utc import utcnow


@mock.patch("superdesk.publish.subscribers.SubscribersService.generate_sequence_number", lambda self, subscriber: 1)
class FTPNinjsFormatterTest(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.formatter = FTPNinjsFormatter()
        init_app(self.app)
        self.maxDiff = None
        self.app.config["EMBED_PRODUCT_FILTERING"] = True

    async def test_picture_formatter(self):
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
                    "href": "pictures/12345-5e448dd1016d1f63a92f0400.jpg",
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

    async def test_picture_formatter_with_original(self):
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
                    "href": "pictures/12345-5e448dd1016d1f63a92f0400.jpg",
                    "mimetype": "image/jpeg",
                    "media": "12345/5e448dd1016d1f63a92f0400.jpg",
                },
                "original": {
                    "href": "pictures/12345-5e448dd1016d1f63a92f0398.jpg",
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

    async def test_embedded_image(self):
        self.app.data.insert(
            "filter_conditions",
            [{"_id": 1, "field": "type", "operator": "eq", "value": "picture", "name": "Picture fc"}],
        )
        self.app.data.insert(
            "content_filters",
            [{"_id": 3, "content_filter": [{"expression": {"fc": [1]}}], "name": "Picture cf"}],
        )
        self.app.data.insert(
            "products",
            [
                {
                    "_id": 1,
                    "content_filter": {"filter_id": 3, "filter_type": "permitting"},
                    "name": "Picture",
                    "product_type": "both",
                }
            ],
        )
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
        editor = Editor3Content(article, "body_html")
        editor.update_item()
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
                "products": [1],
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
                            "href": "pictures/20190405160436-9e0b3096a5792b1e646a6b1e7dad606ccc69"
                            "7b4b686dde76b13b7b64e994f579.jpg",
                        }
                    },
                    "description_text": "Steam rises from the brown coal-fired power plant",
                    "description_html": "<p>Steam rises from the brown coal-fired power plant</p>",
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
            "body_html": '<p>Some text</p>\n<!-- EMBED START Image {id: "editor_0"} -->\n<figure>'
            '<img src="pictures/20190405160436-9e0b3096a5792b1e646a6b1e7dad606ccc697b4b686dd'
            'e76b13b7b64e994f579.jpg" srcset="pictures/20190405160436-9e0b3096a5792b1e646a6b1'
            'e7dad606ccc697b4b686dde76b13b7b64e994f579.jpg 4500w" sizes="80vw" alt="Power plant" '
            'id="editor_0">'
            "<figcaption>Steam rises from the brown coal-fired power plant</figcaption></figure>\n"
            '<!-- EMBED END Image {id: "editor_0"} -->\n<p>More text</p>',
            "service": [{"name": "Australian General News", "code": "a"}],
            "version": "1",
        }
        self.assertEqual(expected, json.loads(doc))

    async def test_embedded_image_rendition_set(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "crop_sizes",
                    "items": [
                        {"is_active": True, "name": "4-3", "width": 800, "height": 600},
                        {"is_active": True, "name": "16-9", "width": 1280, "height": 720},
                    ],
                }
            ],
        )
        self.app.data.insert(
            "filter_conditions",
            [
                {"_id": 1, "field": "type", "operator": "eq", "value": "picture", "name": "Picture fc"},
                {"_id": 2, "field": "type", "operator": "eq", "value": "video", "name": "Video fc"},
            ],
        )
        self.app.data.insert(
            "content_filters",
            [
                {
                    "_id": 3,
                    "content_filter": [{"expression": {"fc": [1]}}, {"expression": {"fc": [2]}}],
                    "name": "Picture cf",
                }
            ],
        )
        self.app.data.insert(
            "products",
            [
                {
                    "_id": 1,
                    "content_filter": {"filter_id": 3, "filter_type": "permitting"},
                    "name": "Picture and Video",
                    "product_type": "both",
                }
            ],
        )
        article = {
            "_id": "urn:newsml:localhost:2020-03-12T15:19:39.654956:e78f3dd6-c096-43d5-9ba0-014e07dc4f1f",
            "associations": {
                "editor_2": {
                    "_id": "urn:newsml:aap.com.au:2023-03-08T10:34:33.291350:bda807fd-466c-4861-a58f-6e18b0d59efd",
                    "media": "20230308100332/video.mp4",
                    "type": "video",
                    "pubstatus": "usable",
                    "renditions": {
                        "original": {
                            "href": "http://acme.com.au/api/upload-raw/20230308100332/video.mp4",
                            "media": "20230308100332/video.mp4",
                            "mimetype": "video/mp4",
                        }
                    },
                },
                "editor_0": {
                    "type": "picture",
                    "_id": "tag:localhost:2019:5c9da5e1-f491-4ffd-a0b5-dd54e9fd870f",
                    "renditions": {
                        "original": {
                            "mimetype": "image/jpeg",
                            "href": "http://acme.com.au/api/upload-raw/20190405160436/original.jpg",
                            "width": 4500,
                            "height": 3000,
                            "poi": {"y": 1770, "x": 2160},
                            "media": "20190405160436/original.jpg",
                        },
                        "4-3": {
                            "href": "http://acme.aap.com.au/api/upload-raw/fourthree.jpg",
                            "width": 800,
                            "height": 600,
                            "mimetype": "image/jpeg",
                            "media": "20230303110348/fourthree.jpg",
                        },
                        "16-9": {
                            "href": "http://acme.com.au/api/upload-raw/sixteennine.jpg",
                            "width": 1280,
                            "height": 720,
                            "mimetype": "image/jpeg",
                            "media": "20230303110348/sixteennine.jpg",
                        },
                    },
                },
            },
            "type": "text",
            "headline": "Test Headline",
            "body_html": '<p>Some text</p>\n<!-- EMBED START Image {id: "editor_0"} -->\n<figure>\n    '
            '<img src="http://acme.com.au/api/upload-raw/20190405160436/9e0b3096a5792b1'
            'e646a6b1e7dad606ccc697b4b686dde76b13b7b64e994f579.jpg" alt="Power plant" />\n    '
            "<figcaption>Steam rises from the brown coal-fired power plant</figcaption>\n</figure>\n"
            '<!-- EMBED END Image {id: "editor_0"} -->\n<p>More text</p><p>and a video</p>'
            '<!-- EMBED START Video {id: "editor_2"} -->\n<figure>\n    <video controls '
            'src="http://acme.com.au/api/upload-raw/20230308100332/71c721fe378ded236e152f2'
            'def27c32af9b0ab49fd5ca38c13b62181ecb0bc7b.mp4" alt="Gladysmp4" width="100%" height="100%" />'
            "\n    <figcaption>Gladysmp4</figcaption>\n</figure>"
            '\n<!-- EMBED END Video {id: "editor_2"} -->',
        }
        editor = Editor3Content(article, "body_html")
        editor.update_item()
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
                            "include_original": False,
                        }
                    }
                ],
                "products": [1],
            },
        )[0]
        expected = {
            "guid": None,
            "version": "1",
            "type": "text",
            "headline": "Test Headline",
            "body_html": '<p>Some text</p>\n<!-- EMBED START Image {id: "editor_0"} -->\n<figure>'
            '<img src="pictures/20230303110348-sixteennine.jpg" '
            'srcset="pictures/20230303110348-fourthree.jpg 800w,'
            'pictures/20230303110348-sixteennine.jpg 1280w" '
            'sizes="80vw" alt="" id="editor_0">'
            '</figure>\n<!-- EMBED END Image {id: "editor_0"} -->\n'
            '<p>More text</p>\n<p>and a video</p>\n<!-- EMBED START Video {id: "editor_1"} -->\n'
            '<figure><video controls="" src="pictures/20230308100332-video.mp4" '
            'title="" id="editor_1"> </video>'
            '</figure>\n<!-- EMBED END Video {id: "editor_1"} -->',
            "associations": {
                "editor_2": {
                    "guid": None,
                    "version": "1",
                    "type": "video",
                    "pubstatus": "usable",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "href": "pictures/20230308100332-video.mp4",
                            "mimetype": "video/mp4",
                            "media": "20230308100332/video.mp4",
                        }
                    },
                },
                "editor_0": {
                    "guid": None,
                    "version": "1",
                    "type": "picture",
                    "priority": 5,
                    "renditions": {
                        "4-3": {
                            "href": "pictures/20230303110348-fourthree.jpg",
                            "width": 800,
                            "height": 600,
                            "mimetype": "image/jpeg",
                            "media": "20230303110348/fourthree.jpg",
                        },
                        "16-9": {
                            "href": "pictures/20230303110348-sixteennine.jpg",
                            "width": 1280,
                            "height": 720,
                            "mimetype": "image/jpeg",
                            "media": "20230303110348/sixteennine.jpg",
                        },
                    },
                },
            },
            "priority": 5,
            "charcount": 30,
            "wordcount": 7,
            "readtime": 0,
        }
        self.assertEqual(expected, json.loads(doc))

    async def test_product_match(self):
        self.app.data.insert(
            "filter_conditions",
            [{"_id": 1, "field": "type", "operator": "eq", "value": "video", "name": "ALL Video fc"}],
        )
        self.app.data.insert(
            "content_filters",
            [{"_id": 3, "content_filter": [{"expression": {"fc": [1]}}], "name": "All Video cf"}],
        )
        self.app.data.insert(
            "products",
            [
                {
                    "_id": 1,
                    "content_filter": {"filter_id": 3, "filter_type": "permitting"},
                    "name": "All Video",
                    "product_type": "both",
                }
            ],
        )
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "crop_sizes",
                    "items": [
                        {"is_active": True, "name": "4-3", "width": 800, "height": 600},
                        {"is_active": True, "name": "16-9", "width": 1280, "height": 720},
                    ],
                }
            ],
        )
        item = {
            "_id": "urn:newsml:localhost:2023-06-07T11:24:33.346929:f46b4120-deab-4798-9a1b-32b7888ca05c",
            "type": "text",
            "version": 1,
            "pubstatus": "usable",
            "format": "HTML",
            "_current_version": 5,
            "firstcreated": "2023-06-07T01:24:33.000Z",
            "versioncreated": "2023-06-07T01:31:02.000Z",
            "guid": "urn:newsml:localhost:2023-06-07T11:24:33.346929:f46b4120-deab-4798-9a1b-32b7888ca05c",
            "unique_id": 41882,
            "unique_name": "#41882",
            "family_id": "urn:newsml:localhost:2023-06-07T11:24:33.346929:f46b4120-deab-4798-9a1b-32b7888ca05c",
            "state": "published",
            "source": "AAP",
            "priority": 6,
            "urgency": 5,
            "genre": [{"qcode": "Article", "name": "Article"}],
            "dateline": {
                "source": "AAP",
                "date": "2023-06-07T01:24:33.000Z",
                "located": {
                    "city": "Wagga Wagga",
                    "state": "New South Wales",
                    "dateline": "city",
                    "tz": "Australia/Sydney",
                    "city_code": "Wagga Wagga",
                    "country_code": "AU",
                    "alt_name": "",
                    "country": "Australia",
                    "state_code": "NSW",
                },
                "text": "WAGGA WAGGA, June 7 AAP -",
            },
            "byline": "Joe Black",
            "place": [
                {
                    "country": "Australia",
                    "world_region": "Oceania",
                    "name": "QLD",
                    "state": "Queensland",
                    "group": "Australia",
                    "qcode": "QLD",
                }
            ],
            "language": "en",
            "operation": "publish",
            "anpa_category": [{"name": "Australian General News", "qcode": "a"}],
            "associations": {
                "featuremedia": {
                    "_id": "tag:localhost:2022:5e76af3a-4575-4108-a5bf-d0c5664422ee",
                    "guid": "tag:localhost:2022:5e76af3a-4575-4108-a5bf-d0c5664422ee",
                    "headline": "Italy F1 GP Auto Racing",
                    "description_text": "Pole position Ferrari",
                    "archive_description": "Pole position Ferrari driver Charles Leclerc",
                    "source": "AP",
                    "original_source": "AP/Reuters",
                    "versioncreated": "2022-12-20T06:14:22+0000",
                    "firstcreated": "2022-09-10T15:10:00+0000",
                    "pubstatus": "usable",
                    "type": "picture",
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/63a15287e6c3ec2d2df751c5.jpg",
                            "media": "63a15287e6c3ec2d2df751c5",
                            "mimetype": "image/jpeg",
                            "width": 3150,
                            "height": 2100,
                        },
                        "baseImage": {
                            "href": "http://localhost:5000/api/upload-raw/63a1528ae6c3ec2d2df751cc?_schema=http",
                            "media": "63a1528ae6c3ec2d2df751cc",
                            "mimetype": "image/jpeg",
                            "width": 1400,
                            "height": 933,
                        },
                        "thumbnail": {
                            "href": "http://localhost:5000/api/upload-raw/63a1528ae6c3ec2d2df751ce?_schema=http",
                            "media": "63a1528ae6c3ec2d2df751ce",
                            "mimetype": "image/jpeg",
                            "width": 180,
                            "height": 120,
                        },
                        "viewImage": {
                            "href": "http://localhost:5000/api/upload-raw/63a1528ae6c3ec2d2df751d0?_schema=http",
                            "media": "63a1528ae6c3ec2d2df751d0",
                            "mimetype": "image/jpeg",
                            "width": 640,
                            "height": 426,
                        },
                        "4-3": {
                            "width": 800,
                            "height": 600,
                            "href": "http://localhost:5000/api/upload-raw/647fdcdbae4a8a99d5d4f167.jpg",
                            "media": "647fdcdbae4a8a99d5d4f167",
                            "mimetype": "image/jpeg",
                        },
                        "16-9": {
                            "width": 1280,
                            "height": 720,
                            "href": "http://localhost:5000/api/upload-raw/647fdcdbae4a8a99d5d4f16a.jpg",
                            "media": "647fdcdbae4a8a99d5d4f16a",
                            "mimetype": "image/jpeg",
                        },
                    },
                    "state": "published",
                    "slugline": "Video Test",
                    "byline": "AP PHOTO",
                    "ednote": "POOL IMAGE",
                    "mimetype": "image/jpeg",
                    "uri": "20220911001701433030",
                    "unique_id": 41837,
                    "unique_name": "#41837",
                    "_current_version": 3,
                    "operation": "publish",
                    "format": "HTML",
                    "priority": 6,
                    "urgency": 5,
                    "genre": [{"qcode": "Article", "name": "Article"}],
                    "language": "en",
                    "_type": "archive",
                    "_latest_version": 3,
                    "alt_text": "Italy F1 GP Auto Racing",
                    "anpa_category": [{"name": "Australian General News", "qcode": "a"}],
                    "subject": [
                        {
                            "qcode": "05010004",
                            "name": "test/examination",
                            "parent": "05010000",
                        }
                    ],
                    "abstract": "<p>Story abstract</p>",
                },
                "editor_0": {
                    "_id": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                    "media": "647fdaebae4a8a99d5d4eab5",
                    "type": "video",
                    "pubstatus": "usable",
                    "format": "HTML",
                    "_current_version": 2,
                    "firstcreated": "2023-06-07T01:18:32+0000",
                    "versioncreated": "2023-06-07T01:18:46+0000",
                    "guid": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                    "unique_id": 41881,
                    "unique_name": "#41881",
                    "family_id": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                    "state": "published",
                    "source": "AAP",
                    "priority": 6,
                    "urgency": 5,
                    "genre": [{"qcode": "Article", "name": "Article"}],
                    "byline": "Joe Black",
                    "place": [
                        {
                            "country": "Australia",
                            "world_region": "Oceania",
                            "name": "QLD",
                            "state": "Queensland",
                            "group": "Australia",
                            "qcode": "QLD",
                        }
                    ],
                    "language": "en",
                    "operation": "publish",
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/647fdaebae4a8a99d5d4eab5.mp4",
                            "media": "647fdaebae4a8a99d5d4eab5",
                            "mimetype": "video/mp4",
                        }
                    },
                    "mimetype": "video/mp4",
                    "alt_text": "Video Alt text",
                    "description_text": "Test video decsription",
                    "expiry": "2023-07-18T17:18:46+0000",
                    "headline": "Test video headline",
                    "version": 2,
                    "_latest_version": 2,
                    "anpa_category": [{"name": "Australian General News", "qcode": "a"}],
                    "subject": [
                        {
                            "qcode": "05010004",
                            "name": "test/examination",
                            "parent": "05010000",
                        }
                    ],
                    "slugline": "Video Test",
                    "abstract": "<p>Story abstract</p>",
                },
                "editor_1": {
                    "_id": "tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c",
                    "guid": "tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c",
                    "headline": "Germany Daily Life",
                    "description_text": "A Valais black-nosed sheep jumps",
                    "archive_description": "A Valais black-nosed sheep jumps into the air on a snow-covered meadow",
                    "source": "AP",
                    "original_source": "AP/DPA",
                    "versioncreated": "2023-03-07T01:04:39+0000",
                    "firstcreated": "2023-01-28T00:00:00+0000",
                    "pubstatus": "usable",
                    "type": "picture",
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/63d84c03b3fae2e407e0decd.jpg",
                            "media": "63d84c03b3fae2e407e0decd",
                            "mimetype": "image/jpeg",
                            "width": 4297,
                            "height": 2600,
                        },
                        "baseImage": {
                            "href": "http://localhost:5000/api/upload-raw/63d84c08b3fae2e407e0dee9?_schema=http",
                            "media": "63d84c08b3fae2e407e0dee9",
                            "mimetype": "image/jpeg",
                            "width": 1400,
                            "height": 847,
                        },
                        "thumbnail": {
                            "href": "http://localhost:5000/api/upload-raw/63d84c08b3fae2e407e0deeb?_schema=http",
                            "media": "63d84c08b3fae2e407e0deeb",
                            "mimetype": "image/jpeg",
                            "width": 198,
                            "height": 120,
                        },
                        "viewImage": {
                            "href": "http://localhost:5000/api/upload-raw/63d84c08b3fae2e407e0deed?_schema=http",
                            "media": "63d84c08b3fae2e407e0deed",
                            "mimetype": "image/jpeg",
                            "width": 640,
                            "height": 387,
                        },
                        "4-3": {
                            "width": 800,
                            "height": 600,
                            "href": "http://localhost:5000/api/upload-raw/64068da64d05f5303c82458b.jpg",
                            "media": "64068da64d05f5303c82458b",
                            "mimetype": "image/jpeg",
                        },
                        "16-9": {
                            "width": 1280,
                            "height": 720,
                            "href": "http://localhost:5000/api/upload-raw/64068da74d05f5303c82458e.jpg",
                            "media": "64068da74d05f5303c82458e",
                            "mimetype": "image/jpeg",
                        },
                    },
                    "state": "published",
                    "slugline": "Video Test",
                    "byline": "AP PHOTO",
                    "ednote": "GERMANY OUT; MANDATORY CREDIT",
                    "mimetype": "image/jpeg",
                    "unique_id": 41842,
                    "unique_name": "#41842",
                    "_current_version": 2,
                    "expiry": "2023-04-17T17:04:39+0000",
                    "operation": "publish",
                    "format": "HTML",
                    "priority": 6,
                    "urgency": 5,
                    "genre": [{"qcode": "Article", "name": "Article"}],
                    "language": "en",
                    "alt_text": "Germany Daily Life",
                    "subject": [
                        {
                            "qcode": "05010004",
                            "name": "test/examination",
                            "parent": "05010000",
                        }
                    ],
                    "version": 2,
                    "_type": "archive",
                    "_latest_version": 2,
                    "anpa_category": [{"name": "Australian General News", "qcode": "a"}],
                    "abstract": "<p>Story abstract</p>",
                },
            },
            "refs": [
                {
                    "key": "featuremedia",
                    "_id": "tag:localhost:2022:5e76af3a-4575-4108-a5bf-d0c5664422ee",
                    "uri": "20220911001701433030",
                    "guid": "tag:localhost:2022:5e76af3a-4575-4108-a5bf-d0c5664422ee",
                    "type": "picture",
                    "source": "AP",
                },
                {
                    "key": "editor_0",
                    "_id": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                    "guid": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                    "type": "video",
                    "source": "AAP",
                },
                {
                    "key": "editor_1",
                    "_id": "tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c",
                    "uri": "20230128001757495826",
                    "guid": "tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c",
                    "type": "picture",
                    "source": "AP",
                },
            ],
            "slugline": "Video Test",
            "subject": [
                {
                    "qcode": "05010004",
                    "name": "test/examination",
                    "parent": "05010000",
                }
            ],
            "abstract": "<p>Story abstract</p>",
            "annotations": [],
            "body_html": '<p>For example, TCP port 631 pened by cupsd process and cupsd only listing on the loopback address (127.0.0.1). Similarly, TCP port 22 opened by sshd process and sshd listing on all IP address for ssh connections:</p>\n<!-- EMBED START Video {id: "editor_0"} -->\n<figure>\n    <video controls src="http://localhost:5000/api/upload-raw/647fdaebae4a8a99d5d4eab5.mp4" alt="Video Alt text" width="100%" height="100%" />\n    <figcaption>Test video decsription</figcaption>\n</figure>\n<!-- EMBED END Video {id: "editor_0"} -->\n<p>The ss command is used to dump socket statistics. It allows showing information similar to netstat. It can display more TCP and state information than other tools. The syntax is:</p>\n<!-- EMBED START Image {id: "editor_1"} -->\n<figure>\n    <img src="http://localhost:5000/api/upload-raw/63d84c03b3fae2e407e0decd.jpg" alt="Germany Daily Life" />\n    <figcaption>A Valais black-nosed sheep jumps into the air on a snow-covered meadow in Langenenslingen, Germany</figcaption>\n</figure>\n<!-- EMBED END Image {id: "editor_1"} -->\n<p>In addition, to above commands one can use the nmap command which is an open source tool for network exploration and security auditing. We are going to use nmap to find and list open ports in Linux:&nbsp;</p>',
            "fields_meta": {
                "headline": {
                    "draftjsState": [
                        {
                            "blocks": [
                                {
                                    "key": "fm5hr",
                                    "text": "Video test story headline",
                                    "type": "unstyled",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [],
                                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                                }
                            ],
                            "entityMap": {},
                        }
                    ]
                },
                "abstract": {
                    "draftjsState": [
                        {
                            "blocks": [
                                {
                                    "key": "2e0dd",
                                    "text": "Story abstract",
                                    "type": "unstyled",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [],
                                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                                }
                            ],
                            "entityMap": {},
                        }
                    ]
                },
                "body_html": {
                    "draftjsState": [
                        {
                            "blocks": [
                                {
                                    "key": "svbd",
                                    "text": "For example, TCP port 631 pened by cupsd process and cupsd only listing on the loopback address (127.0.0.1). Similarly, TCP port 22 opened by sshd process and sshd listing on all IP address for ssh connections:",
                                    "type": "unstyled",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [],
                                    "data": {"MULTIPLE_HIGHLIGHTS": {}},
                                },
                                {
                                    "key": "4g2t1",
                                    "text": " ",
                                    "type": "atomic",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [{"offset": 0, "length": 1, "key": 0}],
                                    "data": {},
                                },
                                {
                                    "key": "794l3",
                                    "text": "The ss command is used to dump socket statistics. It allows showing information similar to netstat. It can display more TCP and state information than other tools. The syntax is:",
                                    "type": "unstyled",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [],
                                    "data": {},
                                },
                                {
                                    "key": "69db4",
                                    "text": " ",
                                    "type": "atomic",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [{"offset": 0, "length": 1, "key": 1}],
                                    "data": {},
                                },
                                {
                                    "key": "ellml",
                                    "text": "In addition, to above commands one can use the nmap command which is an open source tool for network exploration and security auditing. We are going to use nmap to find and list open ports in Linux: ",
                                    "type": "unstyled",
                                    "depth": 0,
                                    "inlineStyleRanges": [],
                                    "entityRanges": [],
                                    "data": {},
                                },
                            ],
                            "entityMap": {
                                "0": {
                                    "type": "MEDIA",
                                    "mutability": "MUTABLE",
                                    "data": {
                                        "media": {
                                            "_id": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                                            "media": "647fdaebae4a8a99d5d4eab5",
                                            "type": "video",
                                            "pubstatus": "usable",
                                            "format": "HTML",
                                            "firstcreated": "2023-06-07T01:18:32+0000",
                                            "versioncreated": "2023-06-07T01:18:46+0000",
                                            "guid": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                                            "unique_id": 41881,
                                            "unique_name": "#41881",
                                            "family_id": "urn:newsml:localhost:2023-06-07T11:18:32.082856:eacdccc3-37fd-4ec1-9aed-5b1e8fb61f99",
                                            "state": "in_progress",
                                            "source": "AAP",
                                            "priority": 6,
                                            "urgency": 0,
                                            "genre": [{"qcode": "Article", "name": "Article"}],
                                            "dateline": {
                                                "date": "2023-06-07T01:18:32+0000",
                                                "source": "AAP",
                                                "located": {
                                                    "city": "Wagga Wagga",
                                                    "state": "New South Wales",
                                                    "dateline": "city",
                                                    "tz": "Australia/Sydney",
                                                    "city_code": "Wagga Wagga",
                                                    "country_code": "AU",
                                                    "alt_name": "",
                                                    "country": "Australia",
                                                    "state_code": "NSW",
                                                },
                                                "text": "WAGGA WAGGA, June 7 AAP -",
                                            },
                                            "byline": "The Great Unwashed",
                                            "place": [
                                                {
                                                    "country": "Australia",
                                                    "world_region": "Oceania",
                                                    "name": "QLD",
                                                    "state": "Queensland",
                                                    "group": "Australia",
                                                    "qcode": "QLD",
                                                }
                                            ],
                                            "language": "en",
                                            "operation": "update",
                                            "renditions": {
                                                "original": {
                                                    "href": "http://localhost:5000/api/upload-raw/647fdaebae4a8a99d5d4eab5.mp4",
                                                    "media": "647fdaebae4a8a99d5d4eab5",
                                                    "mimetype": "video/mp4",
                                                }
                                            },
                                            "mimetype": "video/mp4",
                                            "alt_text": "Video Alt text",
                                            "description_text": "Test video decsription",
                                            "expiry": "2023-07-18T17:18:46+0000",
                                            "headline": "Test video headline",
                                            "version": 2,
                                            "_type": "archive",
                                            "_latest_version": 2,
                                        }
                                    },
                                },
                                "1": {
                                    "type": "MEDIA",
                                    "mutability": "MUTABLE",
                                    "data": {
                                        "media": {
                                            "_id": "tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c",
                                            "guid": "tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c",
                                            "headline": "Germany Daily Life",
                                            "description_text": "A Valais black-nosed sheep jumps into the air on a snow-covered meadow in Langenenslingen, Germany",
                                            "archive_description": "A Valais black-nosed sheep jumps into the air on a snow-covered meadow in Langenenslingen, Germany, Saturday, Jan. 28, 2023. (Thomas Warnack/dpa via AP)",
                                            "source": "AP",
                                            "original_source": "AP/DPA",
                                            "versioncreated": "2023-03-07T01:04:39+0000",
                                            "firstcreated": "2023-01-28T00:00:00+0000",
                                            "pubstatus": "usable",
                                            "type": "picture",
                                            "renditions": {
                                                "original": {
                                                    "href": "http://localhost:5000/api/upload-raw/63d84c03b3fae2e407e0decd.jpg",
                                                    "media": "63d84c03b3fae2e407e0decd",
                                                    "mimetype": "image/jpeg",
                                                    "width": 4297,
                                                    "height": 2600,
                                                },
                                                "baseImage": {
                                                    "href": "http://localhost:5000/api/upload-raw/63d84c08b3fae2e407e0dee9?_schema=http",
                                                    "media": "63d84c08b3fae2e407e0dee9",
                                                    "mimetype": "image/jpeg",
                                                    "width": 1400,
                                                    "height": 847,
                                                },
                                                "thumbnail": {
                                                    "href": "http://localhost:5000/api/upload-raw/63d84c08b3fae2e407e0deeb?_schema=http",
                                                    "media": "63d84c08b3fae2e407e0deeb",
                                                    "mimetype": "image/jpeg",
                                                    "width": 198,
                                                    "height": 120,
                                                },
                                                "viewImage": {
                                                    "href": "http://localhost:5000/api/upload-raw/63d84c08b3fae2e407e0deed?_schema=http",
                                                    "media": "63d84c08b3fae2e407e0deed",
                                                    "mimetype": "image/jpeg",
                                                    "width": 640,
                                                    "height": 387,
                                                },
                                                "4-3": {
                                                    "width": 800,
                                                    "height": 600,
                                                    "href": "http://localhost:5000/api/upload-raw/64068da64d05f5303c82458b.jpg",
                                                    "media": "64068da64d05f5303c82458b",
                                                    "mimetype": "image/jpeg",
                                                },
                                                "16-9": {
                                                    "width": 1280,
                                                    "height": 720,
                                                    "href": "http://localhost:5000/api/upload-raw/64068da74d05f5303c82458e.jpg",
                                                    "media": "64068da74d05f5303c82458e",
                                                    "mimetype": "image/jpeg",
                                                },
                                            },
                                            "state": "in_progress",
                                            "slugline": "Germany Daily Life",
                                            "byline": "AP PHOTO",
                                            "ednote": "GERMANY OUT; MANDATORY CREDIT",
                                            "mimetype": "image/jpeg",
                                            "uri": "20230128001757495826",
                                            "_current_version": 2,
                                            "expiry": "2023-04-17T17:04:39+0000",
                                            "operation": "update",
                                            "format": "HTML",
                                            "priority": 6,
                                            "urgency": None,
                                            "genre": [{"qcode": "Article", "name": "Article"}],
                                            "language": "en",
                                            "alt_text": "Germany Daily Life",
                                            "subject": [
                                                {
                                                    "qcode": "01000000",
                                                    "name": "arts, culture and entertainment",
                                                }
                                            ],
                                            "version": 2,
                                            "_type": "archive",
                                            "_latest_version": 2,
                                        }
                                    },
                                },
                            },
                        }
                    ]
                },
            },
            "headline": "Video test story headline",
            "word_count": 121,
            "firstpublished": "2023-06-07T01:31:31.000Z",
        }
        seq, doc = self.formatter.format(
            item,
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
                "products": [1],
            },
        )[0]
        self.assertIn("editor_0", doc)
        self.assertNotIn("editor_1", doc)
        self.assertNotIn("tag:localhost:2023:4f7e5665-84e3-4cef-9181-addf9bf8474c", doc)
        self.assertIn("featuremedia", doc)
