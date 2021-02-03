# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
from superdesk.tests import TestCase

from superdesk.etree import etree
from superdesk.io.feed_parsers import wordpress_wxr
from unittest import mock
import datetime

FAKE_MEDIA_DATA = {
    "_created": datetime.datetime(2017, 4, 26, 13, 0, 33, tzinfo=datetime.timezone.utc),
    "_etag": "0b135dc3959fe4b09642d02ae733b94af72af5d3",
    "_id": "590099f1cc3a2d2349a785f4",
    "_updated": datetime.datetime(2017, 4, 26, 13, 0, 33, tzinfo=datetime.timezone.utc),
    "media": "590099f1cc3a2d2349a785ee",
    "mimetype": "image/jpeg",
    "renditions": {
        "original": {
            "height": 256,
            "href": "http://test",
            "media": "590099f1cc3a2d2349a785ee",
            "mimetype": "image/jpeg",
            "width": 642,
        },
        "thumbnail": {
            "height": 23,
            "href": "http://test",
            "media": "590099f1cc3a2d2349a785f0",
            "mimetype": "image/jpeg",
            "width": 60,
        },
        "viewImage": {
            "height": 79,
            "href": "http://test",
            "media": "590099f1cc3a2d2349a785f2",
            "mimetype": "image/jpeg",
            "width": 200,
        },
    },
}


def fake_update_renditions(item, url, _):
    update = {
        # we use URL as _id so we can check the value easily
        "_id": url,
        "renditions": {
            "original": {
                "height": 256,
                "href": "http://test",
                "media": "590099f1cc3a2d2349a785ee",
                "mimetype": "image/jpeg",
                "width": 642,
            },
            "thumbnail": {
                "height": 23,
                "href": "http://test",
                "media": "590099f1cc3a2d2349a785f0",
                "mimetype": "image/jpeg",
                "width": 60,
            },
            "viewImage": {
                "height": 79,
                "href": "http://test",
                "media": "590099f1cc3a2d2349a785f2",
                "mimetype": "image/jpeg",
                "width": 200,
            },
        },
        "mimetype": "image/jpeg",
    }
    item.update(update)


class WPWXRTestBase(TestCase):
    @mock.patch.object(wordpress_wxr, "update_renditions", fake_update_renditions)
    def __init__(self, methodname):
        super().__init__(methodname)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with open(fixture, "rb") as f:
            buf = f.read()
        self.ori_file = buf
        parser = etree.XMLParser(recover=True)
        parsed = etree.fromstring(buf, parser)
        self.articles = wordpress_wxr.WPWXRFeedParser().parse(parsed, provider)


class WPWXRTestCase(WPWXRTestBase):

    filename = "wordpress_wxr.xml"

    def test_guid(self):
        self.assertEqual(self.articles[0]["guid"], "http://sdnewtester.org/?p=216")

    def test_firstpublished(self):
        self.assertEqual(
            self.articles[0]["firstpublished"], datetime.datetime(2013, 7, 29, 16, 3, 54, tzinfo=datetime.timezone.utc)
        )

    def test_author(self):
        self.assertEqual(self.articles[0]["author"], "admin")

    def test_headline(self):
        self.assertEqual(self.articles[0]["headline"], "Starafrica to dispose assets for $6 million to clear debt")

    def test_body_html(self):
        expected = (
            "<p>By Tester\nHarare, July 19 (The SDNewTester) - "
            "Cash-strapped StarAfrica Corporation is set to dis"
            "pose its transport company and its stake in Tongaa"
            "t Hulett Botswana for $6 million to offset part of"
            " the companyâs $19.7 million debt.\nBla bla test</p>"
        )
        self.assertEqual(self.articles[0]["body_html"], expected)

    def test_body_html_non_void(self):
        """Check that non void elements are not self closing (which is illegal in HTML 5)

        SDESK-3758
        """
        expected = (
            '<hr/><p>\t\t<img src="http://test"/></p>\t\t<iframe src="https://test.invalid"'
            ' width="750" height="400" frameborder="0" allowfullscreen="allowfull'
            'screen"></iframe>'
        )
        self.assertEqual(self.articles[4]["body_html"], expected)

    def test_keywords(self):
        self.assertEqual(self.articles[0]["keywords"], ["companies"])

    def test_category(self):
        self.assertEqual(
            self.articles[0]["anpa_category"],
            [
                {"qcode": "Business", "name": "Business"},
                {"qcode": "Companies", "name": "Companies"},
                {"qcode": "Economy", "name": "Economy"},
            ],
        )

    def test_attachments(self):
        # in self.articles[1] there is a body, so image should be in associations
        expected = {
            "_id": "http://example.net/image.png",
            "guid": "http://example.net/image.png",
            "ingest_provider": "wpwxr",
            "headline": "test2",
            "alt_text": " ",
            "description_text": " ",
            "mimetype": "image/jpeg",
            "renditions": {
                "original": {
                    "height": 256,
                    "href": "http://test",
                    "media": "590099f1cc3a2d2349a785ee",
                    "mimetype": "image/jpeg",
                    "width": 642,
                },
                "thumbnail": {
                    "height": 23,
                    "href": "http://test",
                    "media": "590099f1cc3a2d2349a785f0",
                    "mimetype": "image/jpeg",
                    "width": 60,
                },
                "viewImage": {
                    "height": 79,
                    "href": "http://test",
                    "media": "590099f1cc3a2d2349a785f2",
                    "mimetype": "image/jpeg",
                    "width": 200,
                },
            },
            "type": "picture",
        }
        self.assertEqual(self.articles[1]["associations"]["featuremedia"], expected)

    def test_attachments_no_body(self):
        # in self.articles[1] there is no body, so item should be an image
        # cf. SDTS-29
        expected = {
            "original": {
                "height": 256,
                "href": "http://test",
                "media": "590099f1cc3a2d2349a785ee",
                "mimetype": "image/jpeg",
                "width": 642,
            },
            "thumbnail": {
                "height": 23,
                "href": "http://test",
                "media": "590099f1cc3a2d2349a785f0",
                "mimetype": "image/jpeg",
                "width": 60,
            },
            "viewImage": {
                "height": 79,
                "href": "http://test",
                "media": "590099f1cc3a2d2349a785f2",
                "mimetype": "image/jpeg",
                "width": 200,
            },
        }
        self.assertNotIn("associations", self.articles[3])
        self.assertEqual(self.articles[3]["renditions"], expected)
        self.assertEqual(self.articles[3]["type"], "picture")

    def test_clrf(self):
        expected = (
            "<p>By Tester</p><p>Harare, July 19 (The SDNewTester) - Cash-strapped"
            " StarAfrica Corporation is set to dispose its transport company and "
            "its stake in Tongaat Hulett Botswana for $6 million to offset part o"
            "f the companyâs $19.7 million debt.</p><hr><p>Bla bla test</p>"
        )
        self.assertEqual(self.articles[2]["body_html"], expected)


class WPWXRThumbnailTestCase(WPWXRTestBase):

    filename = "wordpress_wxr_thumb.xml"

    def test_skipped(self):
        """Check that "attachment" items are skipped"""
        # in the test file are 2 items: one "attachment" and one "post",
        # only the "post" item must be returned
        self.assertEqual(len(self.articles), 1)

    def test_thumbnail(self):
        """Check that thumbnail is retrieved from other item and used as feature media (SDESK-3699)"""
        expected = {
            "type": "picture",
            "ingest_provider": "wpwxr",
            "_id": "https://toto.invalid/attachment.jpg",
            "guid": "https://toto.invalid/attachment.jpg",
            "renditions": {
                "original": {
                    "height": 256,
                    "href": "http://test",
                    "media": "590099f1cc3a2d2349a785ee",
                    "mimetype": "image/jpeg",
                    "width": 642,
                },
                "thumbnail": {
                    "height": 23,
                    "href": "http://test",
                    "media": "590099f1cc3a2d2349a785f0",
                    "mimetype": "image/jpeg",
                    "width": 60,
                },
                "viewImage": {
                    "height": 79,
                    "href": "http://test",
                    "media": "590099f1cc3a2d2349a785f2",
                    "mimetype": "image/jpeg",
                    "width": 200,
                },
            },
            "mimetype": "image/jpeg",
            "description_text": "this is a description",
            "alt_text": "test",
            "headline": "test post",
        }

        self.assertEqual(self.articles[0]["associations"]["featuremedia"], expected)


class FunkeWXRTestCase(WPWXRTestBase):

    filename = "wordpress_wxr_funke.xml"

    def test_body_html(self):
        self.assertTrue(
            self.articles[0]["body_html"].lstrip().startswith("<p><strong"), self.articles[0]["body_html"][:20]
        )
