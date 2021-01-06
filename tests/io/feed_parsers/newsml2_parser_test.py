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
import unittest
import flask

from xml.etree import ElementTree
from superdesk.io.feed_parsers.newsml_2_0 import NewsMLTwoFeedParser
from superdesk.io.subjectcodes import init_app as init_subjects


class BaseNewMLTwoTestCase(unittest.TestCase):
    def setUp(self):
        app = flask.Flask(__name__)
        app.api_prefix = "/api"
        init_subjects(app)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with open(fixture, "rb") as f:
            self.parser = NewsMLTwoFeedParser()
            self.xml = ElementTree.parse(f)
            with app.app_context():
                self.item = self.parser.parse(self.xml.getroot(), provider)


class ReutersTestCase(BaseNewMLTwoTestCase):
    filename = "tag:reuters.com,0000:newsml_L4N1FL0N0:1132689232"

    def test_content(self):
        self.assertEqual(self.item[0].get("headline"), "PRECIOUS-Gold rises as Trump policy fuels safe haven demand")
        self.assertEqual(self.item[0].get("guid"), "tag:reuters.com,0000:newsml_L4N1FL0N0:1132689232")
        self.assertEqual(self.item[0].get("uri"), "tag:reuters.com,0000:newsml_L4N1FL0N0")
        self.assertEqual(self.item[0].get("firstcreated").isoformat(), "2017-01-31T03:47:29")
        self.assertTrue(self.item[0].get("body_html").startswith("<p>(Adds comments, detail)</p>"))
        self.assertNotIn("description_text", self.item[0])
        self.assertNotIn("archive_description", self.item[0])
        self.assertEqual(self.item[0].get("word_count"), 348)

    def test_can_parse(self):
        self.assertTrue(NewsMLTwoFeedParser().can_parse(self.xml.getroot()))


class ResutersResultsTestCase(BaseNewMLTwoTestCase):
    filename = "tag:reuters.com,0000:newsml_ISS149709:1618095828"

    def test_results(self):
        self.assertTrue(
            self.item[0]
            .get("body_html")
            .startswith(
                "<p>Jan 30 (Gracenote) - Results and standings from the Turkish championship matches on Monday <br/>"
            )
        )
        self.assertNotIn("word_count", self.item[0])


class ANSATestCase(BaseNewMLTwoTestCase):
    filename = "ansa-newsmlg2-text.xml"

    def test_language(self):
        self.assertEqual("it", self.item[0]["language"])


class ReutersOptaTestCase(BaseNewMLTwoTestCase):
    filename = "tag:reuters.com,2018:newsml_MTZXEE13ZXCZES:2"

    def test_body(self):
        self.assertTrue(
            self.item[0].get("body_html").startswith("<pre>Jan 3 (OPTA) - Results and fixtures for the " "Primeira")
        )


class IPTCExampleTextTestCase(BaseNewMLTwoTestCase):
    filename = "LISTING 1 A NewsML-G2 News Item.xml"

    def test_news_item_parsing(self):
        self.assertEqual(1, len(self.item))
        item = self.item[0]
        self.assertEqual("urn:newsml:acmenews.com:20161018:US-FINANCE-FED", item["uri"])
        self.assertEqual("2016-10-21T16:25:32-05:00", item["versioncreated"].isoformat())
        self.assertIn("STRICTLY EMBARGOED", item["ednote"])
        self.assertEqual(1, len(item["authors"]))
        self.assertEqual("2016-10-23T12:00:00+00:00", item["embargoed"].isoformat())

    def test_can_parse(self):
        self.assertTrue(self.parser.can_parse(self.xml.getroot()))


class IPTCExamplePackage(BaseNewMLTwoTestCase):
    filename = "LISTING 6 Simple NewsML-G2 Package.xml"

    def test_news_item_parsing(self):
        self.assertEqual(1, len(self.item))

    def test_can_parse(self):
        self.assertTrue(self.parser.can_parse(self.xml.getroot()))


class ANSACultureParser(BaseNewMLTwoTestCase):
    filename = "ansa_culture.xml"

    def test_content_parsing(self):
        self.assertIn("(ANSA) - ROMA, 1 LUG - TEST FROM XAWES", self.item[0]["body_html"])
        self.assertNotIn("urgency", self.item[0])
