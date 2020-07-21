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
from bson import ObjectId
from unittest import mock
from datetime import timedelta

from superdesk.utc import utcnow
from superdesk.tests import TestCase
from superdesk.publish.formatters.ninjs_formatter import NINJSFormatter, NINJS2Formatter
from superdesk.publish import init_app


@mock.patch("superdesk.publish.subscribers.SubscribersService.generate_sequence_number", lambda self, subscriber: 1)
class NinjsFormatterTest(TestCase):
    def setUp(self):
        self.formatter = NINJSFormatter()
        init_app(self.app)
        self.maxDiff = None

    def test_text_formatter(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "locators",
                    "display_name": "Locators",
                    "type": "unmanageable",
                    "unique_field": "qcode",
                    "items": [
                        {
                            "is_active": True,
                            "name": "NSW",
                            "qcode": "NSW",
                            "state": "New South Wales",
                            "country": "Australia",
                            "world_region": "Oceania",
                            "group": "Australia",
                        }
                    ],
                }
            ],
        )
        embargo_ts = utcnow() + timedelta(days=2)
        article = {
            "_id": "tag:aap.com.au:20150613:12345",
            "guid": "tag:aap.com.au:20150613:12345",
            "_current_version": 1,
            "anpa_category": [{"qcode": "a"}],
            "source": "AAP",
            "headline": "This is a test headline",
            "byline": "joe",
            "slugline": "slugline",
            "subject": [
                {"qcode": "02011001", "name": "international court or tribunal", "parent": None},
                {"qcode": "02011002", "name": "extradition"},
            ],
            "anpa_take_key": "take_key",
            "unique_id": "1",
            "body_html": "The story body",
            "type": "text",
            "word_count": "1",
            "priority": 1,
            "profile": "snap",
            "state": "published",
            "urgency": 2,
            "pubstatus": "usable",
            "creditline": "sample creditline",
            "keywords": ["traffic"],
            "abstract": "<p>sample <b>abstract</b></p>",
            "place": [{"name": "NSW", "qcode": "NSW"}],
            "embargo": embargo_ts,
            "embargoed": embargo_ts - timedelta(days=1),
            "body_footer": "<p>call helpline 999 if you are planning to quit smoking</p>",
            "company_codes": [{"name": "YANCOAL AUSTRALIA LIMITED", "qcode": "YAL", "security_exchange": "ASX"}],
            "genre": [{"name": "Article", "qcode": "article"}],
            "flags": {"marked_for_legal": True},
            "extra": {"foo": "test"},
            "annotations": [{"msg": "test"}],
        }
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        expected = {
            "guid": "tag:aap.com.au:20150613:12345",
            "version": "1",
            "place": [{"code": "NSW", "name": "New South Wales"}],
            "pubstatus": "usable",
            "body_html": "The story body<p>call helpline 999 if you are planning to quit smoking</p>",
            "type": "text",
            "subject": [
                {"code": "02011001", "name": "international court or tribunal"},
                {"code": "02011002", "name": "extradition"},
            ],
            "service": [{"code": "a"}],
            "source": "AAP",
            "headline": "This is a test headline",
            "byline": "joe",
            "urgency": 2,
            "priority": 1,
            "embargoed": embargo_ts.isoformat(),
            "profile": "snap",
            "slugline": "slugline",
            "description_text": "sample abstract",
            "description_html": "<p>sample <b>abstract</b></p>",
            "keywords": ["traffic"],
            "organisation": [
                {
                    "name": "YANCOAL AUSTRALIA LIMITED",
                    "rel": "Securities Identifier",
                    "symbols": [{"ticker": "YAL", "exchange": "ASX"}],
                }
            ],
            "genre": [{"name": "Article", "code": "article"}],
            "signal": [{"name": "Content Warning", "code": "cwarn", "scheme": "http://cv.iptc.org/newscodes/signal/"}],
            "extra": {"foo": "test"},
            "charcount": 67,
            "wordcount": 13,
            "readtime": 0,
            "annotations": article["annotations"],
        }
        self.assertEqual(json.loads(doc), expected)

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
                },
                "custom": None,  # simulate custom crop which is too big
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
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        expected = {
            "byline": "MICKEY MOUSE",
            "renditions": {
                "original": {
                    "href": "https://one-api.aap.com.au/api/v3/Assets/20150723001158606583/Original/download",
                    "mimetype": "image/jpeg",
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

    def test_composite_formatter(self):
        article = {
            "guid": "urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c",
            "groups": [
                {"id": "root", "refs": [{"idRef": "main"}, {"idRef": "sidebars"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916",
                            "headline": "WA:Navy steps in with WA asylum-seeker boat",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916",
                        }
                    ],
                    "role": "grpRole:main",
                },
                {
                    "id": "sidebars",
                    "refs": [
                        {
                            "renditions": {
                                "original_source": {
                                    "href": "https://one-api.aap.com.au\
                                        /api/v3/Assets/20150723001158639795/Original/download",
                                    "mimetype": "image/jpeg",
                                },
                                "original": {
                                    "width": 2784,
                                    "height": 4176,
                                    "href": "http://localhost:5000\
                                    /api/upload/55b078b21d41c8e974d17ec5/raw?_schema=http",
                                    "mimetype": "image/jpeg",
                                    "media": "55b078b21d41c8e974d17ec5",
                                },
                                "thumbnail": {
                                    "width": 80,
                                    "height": 120,
                                    "href": "http://localhost:5000\
                                    /api/upload/55b078b41d41c8e974d17ed3/raw?_schema=http",
                                    "mimetype": "image/jpeg",
                                    "media": "55b078b41d41c8e974d17ed3",
                                },
                                "viewImage": {
                                    "width": 426,
                                    "height": 640,
                                    "href": "http://localhost:5000\
                                    /api/upload/55b078b31d41c8e974d17ed1/raw?_schema=http",
                                    "mimetype": "image/jpeg",
                                    "media": "55b078b31d41c8e974d17ed1",
                                },
                                "baseImage": {
                                    "width": 933,
                                    "height": 1400,
                                    "href": "http://localhost:5000\
                                    /api/upload/55b078b31d41c8e974d17ecf/raw?_schema=http",
                                    "mimetype": "image/jpeg",
                                    "media": "55b078b31d41c8e974d17ecf",
                                },
                            },
                            "slugline": "ABC SHOP CLOSURES",
                            "type": "picture",
                            "guid": "urn:newsml:localhost:2015-07-24T15:04:29.589984:"
                            "af3bef9a-5002-492b-a15a-8b460e69b164",
                            "headline": "ABC SHOP CLOSURES",
                            "location": "archive",
                            "itemClass": "icls:picture",
                            "residRef": "urn:newsml:localhost:2015-07-24T15:04:29.589984:"
                            "af3bef9a-5002-492b-a15a-8b460e69b164",
                        }
                    ],
                    "role": "grpRole:sidebars",
                },
            ],
            "description": "",
            "operation": "update",
            "sign_off": "mar",
            "type": "composite",
            "pubstatus": "usable",
            "version_creator": "558379451d41c83ff598a3af",
            "language": "en",
            "guid": "urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c",
            "unique_name": "#145",
            "headline": "WA:Navy steps in with WA asylum-seeker boat",
            "original_creator": "558379451d41c83ff598a3af",
            "source": "AAP",
            "_etag": "b41df79084304219524a092abf07ecba9e1bb2c5",
            "slugline": "Boat",
            "firstcreated": "2015-07-24T05:05:00.000Z",
            "unique_id": 145,
            "versioncreated": "2015-07-24T05:05:14.000Z",
            "_updated": "2015-07-24T05:05:25.000Z",
            "family_id": "urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c",
            "_current_version": 2,
            "_created": "2015-07-24T05:05:00.000Z",
            "version": 2,
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        expected = {
            "headline": "WA:Navy steps in with WA asylum-seeker boat",
            "version": "2",
            "guid": "urn:newsml:localhost:2015-07-24T15:05:00.116047:435c93c2-492c-4668-ab47-ae6e2b9b1c2c",
            "associations": {
                "main": {"guid": "tag:localhost:2015:515b895a-b336-48b2-a506-5ffaf561b916", "type": "text"},
                "sidebars": {
                    "guid": "urn:newsml:localhost:2015-07-24T15:04:29.589984:af3bef9a-5002-492b-a15a-8b460e69b164",
                    "type": "picture",
                },
            },
            "firstcreated": "2015-07-24T05:05:00.000Z",
            "versioncreated": "2015-07-24T05:05:14.000Z",
            "type": "composite",
            "pubstatus": "usable",
            "language": "en",
            "priority": 5,
            "slugline": "Boat",
            "source": "AAP",
        }
        self.assertEqual(expected, json.loads(doc))

    def test_item_with_usable_associations(self):
        article = {
            "_id": "urn:bar",
            "guid": "urn:bar",
            "_current_version": 1,
            "type": "text",
            "associations": {
                "image": {
                    "_id": "urn:foo",
                    "guid": "urn:foo",
                    "pubstatus": "usable",
                    "headline": "Foo",
                    "type": "picture",
                    "task": {},
                    "copyrightholder": "Foo ltd.",
                    "description_text": "Foo picture",
                    "renditions": {
                        "original": {
                            "href": "http://example.com",
                            "width": "100",
                            "height": "80",
                            "mimetype": "image/jpeg",
                            "CropLeft": 0,
                        }
                    },
                }
            },
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        formatted = json.loads(doc)
        self.assertIn("associations", formatted)
        self.assertIn("image", formatted["associations"])
        image = formatted["associations"]["image"]
        self.assertEqual("urn:foo", image["guid"])
        self.assertEqual("Foo", image["headline"])
        self.assertEqual("usable", image["pubstatus"])
        self.assertNotIn("task", image)
        self.assertEqual("Foo ltd.", image["copyrightholder"])
        self.assertEqual("Foo picture", image["description_text"])
        rendition = image["renditions"]["original"]
        self.assertEqual(100, rendition["width"])
        self.assertEqual(80, rendition["height"])
        self.assertEqual("image/jpeg", rendition["mimetype"])
        self.assertNotIn("CropLeft", rendition)

    def test_item_with_empty_associations(self):
        article = {
            "_id": "urn:bar",
            "guid": "urn:bar",
            "_current_version": 1,
            "type": "text",
            "associations": {"image": None},
        }

        _, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        formatted = json.loads(doc)
        self.assertIn("associations", formatted)
        self.assertNotIn("image", formatted["associations"])

    def test_vidible_formatting(self):
        article = {
            "_id": "tag:aap.com.au:20150613:12345",
            "guid": "tag:aap.com.au:20150613:12345",
            "_current_version": 1,
            "source": "AAP",
            "headline": "This is a test headline",
            "slugline": "slugline",
            "unique_id": "1",
            "body_html": "The story body",
            "type": "text",
            "state": "published",
            "pubstatus": "usable",
            "associations": {
                "embedded5346670761": {
                    "uri": "56ba77bde4b0568f54a1ce68",
                    "alt_text": "alternative",
                    "copyrightholder": "Edouard",
                    "copyrightnotice": "Edited with Gimp",
                    "usageterms": "indefinite-usage",
                    "type": "video",
                    "title": "Embed title",
                    "company": "Press Association",
                    "url": "https://videos.vidible.tv/prod/2016-02/09/56ba777ce4b0b6448ed478f5_640x360.mp4",
                    "thumbnail": "https://cdn-ssl.vidible.tv/2016-02/09/56ba777ce4b0b6448ed478f5_60x60.jpg",
                    "duration": 100,
                    "width": 400,
                    "height": 200,
                }
            },
        }
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        expected = {
            "guid": "tag:aap.com.au:20150613:12345",
            "version": "1",
            "pubstatus": "usable",
            "body_html": "The story body",
            "type": "text",
            "headline": "This is a test headline",
            "slugline": "slugline",
            "priority": 5,
            "source": "AAP",
            "charcount": 14,
            "wordcount": 3,
            "readtime": 0,
            "associations": {
                "embedded5346670761": {
                    "guid": "56ba77bde4b0568f54a1ce68",
                    "type": "video",
                    "version": "1",
                    "priority": 5,
                    "body_text": "alternative",
                    "copyrightholder": "Edouard",
                    "copyrightnotice": "Edited with Gimp",
                    "usageterms": "indefinite-usage",
                    "headline": "Embed title",
                    "organisation": [{"name": "Press Association"}],
                    "renditions": {
                        "original": {
                            "href": "https://videos.vidible.tv/prod/2016-02/09/56ba777ce4b0b6448ed478f5_640x360.mp4",
                            "duration": 100,
                            "width": 400,
                            "height": 200,
                        },
                        "thumbnail": {
                            "href": "https://cdn-ssl.vidible.tv/2016-02/09/56ba777ce4b0b6448ed478f5_60x60.jpg"
                        },
                    },
                }
            },
        }
        self.assertEqual(json.loads(doc), expected)

    def test_copyright_holder_notice(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "rightsinfo",
                    "items": [
                        {
                            "is_active": True,
                            "name": "default",
                            "copyrightHolder": "copyright holder",
                            "copyrightNotice": "copyright notice",
                            "usageTerms": "",
                        }
                    ],
                }
            ],
        )

        article = {"_id": "urn:bar", "_current_version": 1, "guid": "urn:bar", "type": "text"}

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        self.assertEqual("copyright holder", data["copyrightholder"])
        self.assertEqual("copyright notice", data["copyrightnotice"])
        self.assertEqual("", data["usageterms"])

    def test_body_html(self):
        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "body_html": (250 * 6 - 40) * "word ",
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        self.assertEqual(data["charcount"], 7300)
        self.assertEqual(data["wordcount"], 1460)
        self.assertEqual(data["readtime"], 6)

    def test_body_text(self):
        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "body_text": (250 * 7 - 40) * "word ",
        }

        data = self._format(article)

        self.assertEqual(data["charcount"], 8550)
        self.assertEqual(data["wordcount"], 1710)
        self.assertEqual(data["readtime"], 7)

        # check japanese
        article["language"] = "ja"
        article["body_text"] = 5000 * "x"
        data = self._format(article)
        self.assertEqual(data["readtime"], 8)

        article["body_text"] = 5000 * " "
        data = self._format(article)
        self.assertEqual(data["readtime"], 0)

    def _format(self, article):
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        return json.loads(doc)

    def test_empty_amstract(self):
        article = {"_id": "urn:bar", "_current_version": 1, "guid": "urn:bar", "type": "text", "abstract": ""}

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        self.assertEqual(data["description_html"], "")
        self.assertEqual(data["description_text"], "")

    def test_authors(self):
        self.app.data.insert(
            "users",
            [
                {
                    "_id": "test_id",
                    "username": "author 1",
                    "display_name": "author 1",
                    "is_author": True,
                    "job_title": "writer_code",
                    "biography": "bio 1",
                    "facebook": "johnsmith",
                    "twitter": "@smith_john",
                    "instagram": "john_s",
                    "picture_url": "http://example.com",
                },
                {
                    "_id": "test_id_2",
                    "username": "author 2",
                    "display_name": "author 2",
                    "is_author": True,
                    "job_title": "reporter_code",
                    "biography": "bio 2",
                },
            ],
        )

        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "job_titles",
                    "display_name": "Job Titles",
                    "type": "manageable",
                    "unique_field": "qcode",
                    "items": [
                        {"is_active": True, "name": "Writer", "qcode": "writer_code"},
                        {"is_active": True, "name": "Reporter", "qcode": "reporter_code"},
                    ],
                    "schema": {"name": {}, "qcode": {}},
                }
            ],
        )

        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "authors": [
                {
                    "_id": ["test_id", "writer"],
                    "role": "writer",
                    "name": "Writer",
                    "parent": "test_id",
                    "sub_label": "author 1",
                },
                {
                    "_id": ["test_id_2", "writer"],
                    "role": "photographer",
                    "name": "photographer",
                    "parent": "test_id_2",
                    "sub_label": "author 2",
                },
            ],
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        expected = [
            {
                "code": "test_id",
                "name": "author 1",
                "role": "writer",
                "jobtitle": {"qcode": "writer_code", "name": "Writer"},
                "biography": "bio 1",
                "facebook": "johnsmith",
                "twitter": "@smith_john",
                "instagram": "john_s",
                "avatar_url": "http://example.com",
            },
            {
                "code": "test_id_2",
                "name": "author 2",
                "role": "photographer",
                "jobtitle": {"qcode": "reporter_code", "name": "Reporter"},
                "biography": "bio 2",
            },
        ]
        self.assertEqual(data["authors"], expected)

    def test_author_missing_parent(self):
        """Test that older items with missing parent don't make the formatter crashing"""
        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "authors": [
                {"_id": ["test_id", "writer"], "role": "writer", "name": "Writer", "sub_label": "author 1"},
                {
                    "_id": ["test_id_2", "writer"],
                    "role": "photographer",
                    "name": "photographer",
                    "sub_label": "author 2",
                },
            ],
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        expected = {
            "guid": "urn:bar",
            "version": "1",
            "type": "text",
            "priority": 5,
            "authors": [
                {"code": "Writer", "name": "Writer", "role": "writer", "biography": ""},
                {"code": "photographer", "name": "photographer", "role": "photographer", "biography": ""},
            ],
        }

        self.assertEqual(data, expected)

    def test_place(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "locators",
                    "display_name": "Locators",
                    "type": "unmanageable",
                    "unique_field": "qcode",
                    "items": [
                        {
                            "is_active": True,
                            "name": "JPN",
                            "qcode": "JPN",
                            "state": "",
                            "country": "Japan",
                            "world_region": "Asia",
                            "group": "Rest Of World",
                        },
                        {"is_active": True, "name": "SAM", "qcode": "SAM", "group": "Rest Of World"},
                        {
                            "is_active": True,
                            "name": "UK",
                            "qcode": "UK",
                            "state": "",
                            "country": "",
                            "world_region": "Europe",
                            "group": "Rest Of World",
                        },
                    ],
                }
            ],
        )
        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "place": [{"name": "JPN", "qcode": "JPN"}],
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        self.assertEqual(data["place"], [{"code": "JPN", "name": "Japan"}])

        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "place": [{"name": "SAM", "qcode": "SAM"}],
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        self.assertEqual(data["place"], [{"code": "SAM", "name": "Rest Of World"}])

        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "place": [{"name": "UK", "qcode": "UK"}],
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        data = json.loads(doc)

        self.assertEqual(data["place"], [{"code": "UK", "name": "Europe"}])

    def test_translations(self):
        """Check that fields are correctly translated"""
        article = {
            "_id": "5a68a134cc3a2d4bd6399177",
            "type": "text",
            "guid": "test",
            "genre": [
                {
                    "name": "Education",
                    "qcode": "genre_custom:Education",
                    "translations": {
                        "name": {"de": "Weiterbildung", "it": "Educazione finanziaria", "ja": "トレーニング用教材"}
                    },
                    "scheme": "genre_custom",
                }
            ],
            "language": "ja",
            "headline": "test",
            "body_html": "<p>test ter</p>",
            "subject": [
                {
                    "name": "Outcome orientated solutions",
                    "parent": "subject:01000000",
                    "qcode": "subject:01000002",
                    "translations": {
                        "name": {"de": "Ergebnisorientiert", "it": "Orientato ai risultati ", "ja": "アウトカム・オリエンティッド"}
                    },
                    "scheme": "subject_custom",
                },
                {
                    "name": "Austria",
                    "qcode": "country_custom:1001002",
                    "translations": {"name": {"de": "\u00d6sterreich", "it": "Austria", "ja": "オーストリア"}},
                    "scheme": "country_custom",
                },
                {
                    "name": "Asia ex Japan",
                    "qcode": "region_custom:Asia ex Japan",
                    "translations": {"name": {"de": "Asien exkl. Japan", "it": "Asia escl. Giappone", "ja": "日本除くアジア"}},
                    "scheme": "region_custom",
                },
                {"name": "no translations", "qcode": "test", "translations": None, "scheme": "test"},
            ],
        }
        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        expected_genre = [{"code": "genre_custom:Education", "name": "トレーニング用教材", "scheme": "genre_custom"}]
        self.assertEqual(ninjs["genre"], expected_genre)
        expected_subject = [
            {"code": "subject:01000002", "name": "アウトカム・オリエンティッド", "scheme": "subject_custom"},
            {"code": "country_custom:1001002", "name": "オーストリア", "scheme": "country_custom"},
            {"code": "region_custom:Asia ex Japan", "name": "日本除くアジア", "scheme": "region_custom"},
            {"code": "test", "name": "no translations", "scheme": "test"},
        ]
        self.assertEqual(ninjs["subject"], expected_subject)

    def test_place_geonames(self):
        article = {
            "_id": "urn:bar",
            "_current_version": 1,
            "guid": "urn:bar",
            "type": "text",
            "place": [
                {
                    "name": "Kobeřice",
                    "code": "3073493",
                    "scheme": "geonames",
                    "state": "Moravskoslezský kraj",
                    "country": "Česko",
                    "state_code": "80",
                    "country_code": "CZ",
                    "location": {"lat": 49.98548, "lon": 18.05212},
                }
            ],
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)

        self.assertEqual({"name": "Kobeřice", "code": "3073493", "scheme": "geonames"}, ninjs["place"][0])

    def test_custom_media(self):
        """Test that custom media are put in "groups" field and not associations (SDESK-2955)"""
        self.app.data.insert(
            "content_types",
            [
                {
                    "_id": ObjectId("5ba11fec0d6f1301ac3cbd13"),
                    "label": "custom media field multi",
                    "editor": {
                        "slugline": {"order": 2, "sdWidth": "full"},
                        "headline": {"order": 3, "formatOptions": []},
                        "custom_media_field_multi_1": {"order": 1},
                    },
                    "schema": {
                        "headline": {"type": "string", "required": False, "maxlength": 64, "nullable": True},
                        "slugline": {"type": "string", "required": False, "maxlength": 24, "nullable": True},
                        "custom_media_field_multi_1": {
                            "type": "media",
                            "required": False,
                            "enabled": True,
                            "nullable": True,
                        },
                    },
                }
            ],
        )
        article = {
            "_id": "5ba1224e0d6f13056bd82d50",
            "type": "text",
            "version": 1,
            "profile": "5ba11fec0d6f1301ac3cbd13",
            "format": "HTML",
            "template": "5ba11fec0d6f1301ac3cbd15",
            "headline": "custom media field multi",
            "slugline": "test custom media2",
            "guid": "123",
            "associations": {
                "custom_media_field_multi_1--1": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "abc",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                },
                "custom_media_field_multi_1--2": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/456.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "cde",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                },
            },
        }

        expected = {
            "associations": {
                "custom_media_field_multi_1--1": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "version": "1",
                },
                "custom_media_field_multi_1--2": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/456.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "version": "1",
                },
            },
            "extra_items": {
                "custom_media_field_multi_1": {
                    "type": "media",
                    "items": [
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/123.jpg",
                                    "media": "abc",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "version": "1",
                        },
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/456.jpg",
                                    "media": "cde",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "version": "1",
                        },
                    ]
                }
            },
            "guid": "123",
            "headline": "custom media field multi",
            "priority": 5,
            "profile": "custommediafieldmulti",
            "slugline": "test custom media2",
            "type": "text",
            "version": "1",
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        self.assertEqual(ninjs, expected)

    # Keep only the original POI and remove all other POI.
    def test_picture_poi(self):
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "crop_sizes",
                    "items": [
                        {"is_active": True, "name": "FIXME", "width": 10000, "height": 10000},
                    ],
                }
            ],
        )
        self.app.data.insert(
            "content_types",
            [
                {
                    "_id": ObjectId("5ba11fec0d6f1301ac3cbd13"),
                    "label": "custom media field multi",
                    "editor": {
                        "slugline": {"order": 2, "sdWidth": "full"},
                        "headline": {"order": 3, "formatOptions": []},
                        "feature_media": {"order": 1},
                    },
                    "schema": {
                        "headline": {"type": "string", "required": False, "maxlength": 64, "nullable": True},
                        "slugline": {"type": "string", "required": False, "maxlength": 24, "nullable": True},
                        "feature_media": {
                            "type": "media",
                            "required": False,
                            "enabled": True,
                            "nullable": True,
                        },
                    },
                }
            ],
        )
        article = {
            "_id": "5ba1224e0d6f13056bd82d50",
            "type": "text",
            "version": 1,
            "profile": "5ba11fec0d6f1301ac3cbd13",
            "format": "HTML",
            "template": "5ba11fec0d6f1301ac3cbd15",
            "headline": "custom media field multi",
            "slugline": "test custom media2",
            "guid": "123",
            "associations": {
                "featuremedia": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                            "poi": {
                                "x": 500,
                                "y": 300,
                            },
                        },
                        "FIXME": {
                            "href": "http://localhost:5000/api/upload-raw/234.jpg",
                            "media": "bcd",
                            "mimetype": "image/jpeg",
                            "width": 500,
                            "height": 300,
                            "poi": {
                                "x": 400,
                                "y": 200,
                            },
                        },
                    },
                    "media": "abc",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                },
            },
        }

        expected = {
            "associations": {
                "featuremedia": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "poi": {
                                "x": 500,
                                "y": 300,
                            },
                        },
                        "FIXME": {
                            "height": 300,
                            "href": "http://localhost:5000/api/upload-raw/234.jpg",
                            "media": "bcd",
                            "mimetype": "image/jpeg",
                            "width": 500,
                        },
                    },
                    "type": "picture",
                    "version": "1",
                },
            },
            "guid": "123",
            "headline": "custom media field multi",
            "priority": 5,
            "profile": "custommediafieldmulti",
            "slugline": "test custom media2",
            "type": "text",
            "version": "1",
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        self.assertEqual(ninjs, expected)

    def test_custom_related_items(self):
        self.app.data.insert(
            "content_types",
            [
                {
                    "_id": ObjectId("5ba11fec0d6f1301ac3cbd13"),
                    "label": "custom related content",
                    "editor": {
                        "slugline": {"order": 2, "sdWidth": "full"},
                        "headline": {"order": 3, "formatOptions": []},
                        "custom_related_content": {"order": 1},
                    },
                    "schema": {
                        "headline": {"type": "string", "required": False, "maxlength": 64, "nullable": True},
                        "slugline": {"type": "string", "required": False, "maxlength": 24, "nullable": True},
                        "custom_related_content": {
                            "type": "related_content",
                            "required": False,
                            "enabled": True,
                            "nullable": True,
                        },
                    },
                }
            ],
        )
        self.app.data.insert("vocabularies", [
            {"_id": "custom_related_content", "field_type": "related_content"},
        ])

        article = {
            "_id": "5ba1224e0d6f13056bd82d50",
            "type": "text",
            "version": 1,
            "profile": "5ba11fec0d6f1301ac3cbd13",
            "format": "HTML",
            "template": "5ba11fec0d6f1301ac3cbd15",
            "headline": "custom related content",
            "slugline": "test custom related content",
            "guid": "123",
            "associations": {
                "custom_related_content--1": {
                    "type": "text",
                    "_id": "guid1",
                    "order": 1,
                },
                "custom_related_content--2": {
                    "type": "picture",
                    "_id": "guid2",
                    "order": 2,
                },
            },
        }

        self.app.data.insert("archive", [
            {
                "_id": "guid1",
                "guid": "guid1",
                "type": "text",
                "language": "en",
                "associations": {
                    "featuredmedia": {
                        "type": "picture",
                    },
                },
            },
            {
                "_id": "guid2",
                "guid": "guid2",
                "type": "picture",
            },
        ])

        expected = {
            "associations": {
                "custom_related_content--1": {
                    "guid": "guid1",
                    "version": "1",
                    "type": "text",
                    "language": "en",
                    "priority": 5,
                    "order": 1,
                },
                "custom_related_content--2": {
                    "guid": "guid2",
                    "version": "1",
                    "type": "picture",
                    "priority": 5,
                    "order": 2,
                },
            },
            "extra_items": {
                "custom_related_content": {
                    "type": "related_content",
                    "items": [
                        {
                            "guid": "guid1",
                            "version": "1",
                            "type": "text",
                            "language": "en",
                            "priority": 5,
                            "order": 1,
                        },
                        {
                            "guid": "guid2",
                            "version": "1",
                            "type": "picture",
                            "priority": 5,
                            "order": 2,
                        }
                    ]
                }
            },
            "guid": "123",
            "headline": "custom related content",
            "priority": 5,
            "profile": "customrelatedcontent",
            "slugline": "test custom related content",
            "type": "text",
            "version": "1",
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        self.assertEqual(ninjs, expected)

    def test_custom_media_ordering_in_extra_fields(self):
        """Test that custom media items are in right order inside extra field SDESK-4423"""
        self.app.data.insert(
            "content_types",
            [
                {
                    "_id": ObjectId("5ba11fec0d6f1301ac3cbd13"),
                    "label": "custom media field multi",
                    "editor": {
                        "slugline": {"order": 2, "sdWidth": "full"},
                        "headline": {"order": 3, "formatOptions": ["underline", "link", "bold"]},
                        "custom_media_field_multi_1": {"order": 1},
                    },
                    "schema": {
                        "headline": {"type": "string", "required": False, "maxlength": 64, "nullable": True},
                        "slugline": {"type": "string", "required": False, "maxlength": 24, "nullable": True},
                        "custom_media_field_multi_1": {
                            "type": "media",
                            "required": False,
                            "enabled": True,
                            "nullable": True,
                        },
                    },
                }
            ],
        )
        article = {
            "_id": "5ba1224e0d6f13056bd82d50",
            "type": "text",
            "version": 1,
            "profile": "5ba11fec0d6f1301ac3cbd13",
            "format": "HTML",
            "template": "5ba11fec0d6f1301ac3cbd15",
            "headline": "custom media field multi",
            "slugline": "test custom media2",
            "guid": "123",
            "associations": {
                "custom_media_field_multi_1--1": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "abc",
                    "type": "picture",
                    "order": 1,
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                },
                "custom_media_field_multi_1--2": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/456.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "cde",
                    "type": "picture",
                    "order": 2,
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                },
                "custom_media_field_multi_1--3": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/345.jpg",
                            "media": "efg",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "efg",
                    "type": "picture",
                    "order": 0,
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                },
            },
        }

        expected = {
            "associations": {
                "custom_media_field_multi_1--1": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "order": 1,
                    "version": "1",
                },
                "custom_media_field_multi_1--2": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/456.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "order": 2,
                    "version": "1",
                },
                "custom_media_field_multi_1--3": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/345.jpg",
                            "media": "efg",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "order": 0,
                    "version": "1",
                },
            },
            "extra_items": {
                "custom_media_field_multi_1": {
                    "type": "media",
                    "items": [
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/345.jpg",
                                    "media": "efg",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "order": 0,
                            "version": "1",
                        },
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/123.jpg",
                                    "media": "abc",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "order": 1,
                            "version": "1",
                        },
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/456.jpg",
                                    "media": "cde",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "order": 2,
                            "version": "1",
                        },
                    ]
                }
            },
            "guid": "123",
            "headline": "custom media field multi",
            "priority": 5,
            "profile": "custommediafieldmulti",
            "slugline": "test custom media2",
            "type": "text",
            "version": "1",
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        self.assertEqual(ninjs, expected)

    def test_custom_related_items_ordering_in_associations(self):
        """Test that custom related items are in right order inside associations SDESK-4463"""
        self.app.data.insert(
            "content_types",
            [
                {
                    "_id": ObjectId("5ba11fec0d6f1301ac3cbd13"),
                    "label": "custom related content",
                    "editor": {
                        "slugline": {"order": 2, "sdWidth": "full"},
                        "headline": {"order": 3, "formatOptions": ["underline", "link", "bold"]},
                        "custom_related_content": {"order": 1},
                    },
                    "schema": {
                        "headline": {"type": "string", "required": False, "maxlength": 64, "nullable": True},
                        "slugline": {"type": "string", "required": False, "maxlength": 24, "nullable": True},
                        "custom_related_content": {
                            "type": "related_content",
                            "required": False,
                            "enabled": True,
                            "nullable": True,
                        },
                    },
                }
            ],
        )
        article = {
            "_id": "5ba1224e0d6f13056bd82d50",
            "type": "text",
            "version": 1,
            "profile": "5ba11fec0d6f1301ac3cbd13",
            "format": "HTML",
            "template": "5ba11fec0d6f1301ac3cbd15",
            "headline": "custom related content",
            "slugline": "test custom related content",
            "guid": "123",
            "associations": {
                "custom_related_content--1": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "abc",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "order": 1,
                    "_type": "archive",
                },
                "custom_related_content--3": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/345.jpg",
                            "media": "efg",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "efg",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "order": 3,
                    "_type": "archive",
                },
                "custom_related_content--2": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/456.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "cde",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "order": 2,
                    "_type": "archive",
                },
                "custom_related_content--21": {
                    "renditions": {
                        "original": {
                            "href": "http://localhost:5000/api/upload-raw/4567.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                            "height": 331,
                        }
                    },
                    "media": "cde",
                    "type": "picture",
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "order": 21,
                    "_type": "archive",
                },
            },
        }

        expected = {
            "associations": {
                "custom_related_content--1": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/123.jpg",
                            "media": "abc",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "version": "1",
                    "order": 1,
                },
                "custom_related_content--2": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/456.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "version": "1",
                    "order": 2,
                },
                "custom_related_content--3": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/345.jpg",
                            "media": "efg",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "version": "1",
                    "order": 3,
                },
                "custom_related_content--21": {
                    "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                    "priority": 5,
                    "renditions": {
                        "original": {
                            "height": 331,
                            "href": "http://localhost:5000/api/upload-raw/4567.jpg",
                            "media": "cde",
                            "mimetype": "image/jpeg",
                            "width": 550,
                        }
                    },
                    "type": "picture",
                    "version": "1",
                    "order": 21,
                },
            },
            "extra_items": {
                "custom_related_content": {
                    "type": "related_content",
                    "items": [
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/123.jpg",
                                    "media": "abc",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "version": "1",
                            "order": 1,
                        },
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/456.jpg",
                                    "media": "cde",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "version": "1",
                            "order": 2,
                        },
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/345.jpg",
                                    "media": "efg",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "version": "1",
                            "order": 3,
                        },
                        {
                            "guid": "tag:localhost:5000:2018:3710ef88-9567-4dbb-a96b-cb53df15b66e",
                            "priority": 5,
                            "renditions": {
                                "original": {
                                    "height": 331,
                                    "href": "http://localhost:5000/api/upload-raw/4567.jpg",
                                    "media": "cde",
                                    "mimetype": "image/jpeg",
                                    "width": 550,
                                }
                            },
                            "type": "picture",
                            "version": "1",
                            "order": 21,
                        },
                    ]
                }
            },
            "guid": "123",
            "headline": "custom related content",
            "priority": 5,
            "profile": "customrelatedcontent",
            "slugline": "test custom related content",
            "type": "text",
            "version": "1",
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        self.assertEqual(ninjs, expected)

    def test_empty_genre(self):
        seq, doc = self.formatter.format({
            "type": "text",
            "guid": "foo",
            "genre": None,
        }, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)
        self.assertIsNotNone(ninjs)


@mock.patch("superdesk.publish.subscribers.SubscribersService.generate_sequence_number", lambda self, subscriber: 1)
class Ninjs2FormatterTest(TestCase):

    def setUp(self):
        self.formatter = NINJS2Formatter()

    def test_format_type(self):
        self.assertEqual('ninjs2', self.formatter.format_type)

    def test_correction_sequence_number(self):
        article = {
            'guid': 'bar',
            'type': 'text',
            'correction_sequence': 2,
            'rewrite_sequence': 1,
            'rewrite_of': 'foo',
            'version': 5,
        }

        seq, doc = self.formatter.format(article, {"name": "Test Subscriber"})[0]
        ninjs = json.loads(doc)

        self.assertEqual('2', ninjs.get('version'))
        self.assertEqual(1, ninjs.get('rewrite_sequence'))
        self.assertEqual('foo', ninjs.get('rewrite_of'))
