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
import flask
import unittest

from datetime import timedelta

from superdesk.tests import AppTestCase
from superdesk.io.feeding_services import OLD_CONTENT_MINUTES
from superdesk.utc import utcnow
from superdesk.etree import etree
from superdesk.text_utils import get_word_count, get_char_count
from superdesk.io.registry import registered_feed_parsers
from superdesk.io.feed_parsers.newsml_1_2 import NewsMLOneFeedParser
from superdesk.io.feed_parsers.newsml_2_0 import NewsMLTwoFeedParser
from superdesk.io.feed_parsers.nitf import NITFFeedParser
from superdesk.io.feeding_services.file_service import FileFeedingService


def get_etree(filename):
    dirname = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dirname, "fixtures", filename)) as f:
        return etree.fromstring(f.read().encode("utf-8"))


class UtilsTest(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.config[OLD_CONTENT_MINUTES] = 10
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)

    def test_get_word_count(self):
        self.assertEqual(2, get_word_count("plain text"), "plain text")
        self.assertEqual(2, get_word_count("<p> html text </p>"), "paragraph")

        self.assertEqual(
            22,
            get_word_count(
                '<doc><p xml:lang="en-US">The weather was superb today in Norfolk, Virginia. Made me want to take\n'
                'out my boat, manufactured by the <org value="acm" idsrc="iptc.org">Acme Boat Company</org>.</p></doc>'
            ),
        )

    def test_get_char_count(self):
        self.assertEqual(10, get_char_count("plain text"))
        self.assertEqual(11, get_char_count("<p> html text </p>"))

        self.assertEqual(
            123,
            get_char_count(
                '<doc><p xml:lang="en-US">The weather was superb today in Norfolk, Virginia. Made me want to take\n'
                'out my boat, manufactured by the <org value="acm" idsrc="iptc.org">Acme Boat Company</org>.</p></doc>'
            ),
        )

    def test_get_xml_parser_newsmlg2(self):
        etree = get_etree("snep.xml")
        self.assertIsInstance(
            FileFeedingService().get_feed_parser({"feed_parser": "newsml2"}, etree), NewsMLTwoFeedParser
        )

    def test_get_xml_parser_nitf(self):
        etree = get_etree("nitf-fishing.xml")
        self.assertIsInstance(FileFeedingService().get_feed_parser({"feed_parser": "nitf"}, etree), NITFFeedParser)

    def test_get_xml_parser_newsml12(self):
        etree = get_etree("afp.xml")
        self.assertIsInstance(
            FileFeedingService().get_feed_parser({"feed_parser": "newsml12"}, etree), NewsMLOneFeedParser
        )

    def test_is_old_content(self):
        service = FileFeedingService()
        self.assertFalse(service.is_old_content(utcnow()))
        self.assertTrue(service.is_old_content(utcnow() - timedelta(minutes=11)))


class ItemTest(AppTestCase):
    def setUpFixture(self, filename):
        self.tree = get_etree(filename)
        provider = {"name": "Test"}

        for parser in registered_feed_parsers.values():
            if parser.can_parse(self.tree):
                self.item = parser.parse(self.tree, provider)[0]


class TextParserTest(ItemTest):
    def setUp(self):
        super().setUp()
        self.setUpFixture("text.xml")

    def test_instance(self):
        self.assertTrue(self.item)

    def test_parse_id(self):
        self.assertEqual("tag:reuters.com,0000:newsml_L4N0BT5PJ:263518268", self.item.get("guid"))
        self.assertEqual("263518268", self.item.get("version"))
        self.assertEqual(3, self.item.get("priority"))

    def test_parse_item_meta(self):
        self.assertEqual("text", self.item.get("type"))
        self.assertEqual("2013-03-01T15:09:04+00:00", self.item.get("versioncreated").isoformat())
        self.assertEqual("2013-03-01T15:09:04+00:00", self.item.get("firstcreated").isoformat())
        self.assertEqual("Editorial Note", self.item.get("ednote"))

    def test_parse_content_meta(self):
        self.assertEqual(3, self.item.get("urgency"))
        self.assertEqual("SOCCER-ENGLAND/CHELSEA-BENITEZ", self.item["slugline"])
        self.assertEqual(
            "Soccer-Smiling Benitez pleads for support " "after midweek outburst against opponent",
            self.item["headline"],
        )
        self.assertNotIn("description_text", self.item)
        self.assertNotIn("archive_description", self.item)

    def test_content_set(self):
        self.assertEqual("<p>By Toby Davis</p>", self.item.get("body_html"))
        self.assertEqual(569, self.item.get("word_count"))
        self.assertIsInstance(self.item.get("body_html"), type(""))

    def test_language(self):
        self.assertEqual("en", self.item.get("language"))

    def test_subject(self):
        self.assertEqual(2, len(self.item.get("subject")))
        self.assertIn({"qcode": "15054000", "name": "soccer"}, self.item.get("subject"))

    def test_pubstatus(self):
        self.assertEqual("usable", self.item.get("pubstatus"))


class PictureParserTest(ItemTest):
    def setUp(self):
        super().setUp()
        self.setUpFixture("picture.xml")

    def test_type(self):
        self.assertEqual("picture", self.item.get("type"))

    def test_content_set(self):
        self.assertEqual(3, len(self.item.get("renditions")))
        self.assertEqual(4, self.item.get("priority"))
        remote = self.item.get("renditions").get("baseImage")
        self.assertTrue(remote)
        self.assertEqual("tag:reuters.com,0000:binary_GM1E9341HD701-BASEIMAGE", remote.get("residRef"))
        self.assertEqual(772617, remote.get("sizeinbytes"))
        self.assertEqual("image/jpeg", remote.get("mimetype"))
        self.assertEqual(
            "http://content.reuters.com/auth-server/content/tag:reuters.com,0000:newsml_GM1E9341HD701:360624134/tag:reuters.com,0000:binary_GM1E9341HD701-BASEIMAGE",
            remote.get("href"),
        )  # noqa
        self.assertIn(
            "A woman casts her ballot inside a polling station in Kenya's town of Gatundu "
            "March 4, 2013. Polling stations opened up to Kenyans on Monday for a tense "
            "presidential election that will test whether the east African nation can repair "
            "its damaged reputation after the tribal blood-letting that followed a "
            "2007 poll.    REUTERS/Marko Djurica (KENYA - Tags: POLITICS ELECTIONS)",
            self.item["description_text"],
        )
        self.assertIn(
            "A woman casts her ballot inside a polling station in Kenya's town of Gatundu "
            "March 4, 2013. Polling stations opened up to Kenyans on Monday for a tense "
            "presidential election that will test whether the east African nation can repair "
            "its damaged reputation after the tribal blood-letting that followed a "
            "2007 poll.    REUTERS/Marko Djurica (KENYA - Tags: POLITICS ELECTIONS)",
            self.item["archive_description"],
        )

    def test_byline(self):
        self.assertEqual("MARKO DJURICA", self.item.get("byline"))

    def test_place(self):
        self.assertEqual(2, len(self.item.get("place")))
        self.assertIn({"name": "NAIROBI"}, self.item["place"])
        self.assertIn({"name": "Kenya"}, self.item["place"])


class SNEPParserTest(ItemTest):
    def setUp(self):
        super().setUp()
        self.setUpFixture("snep.xml")

    def test_content_set(self):
        self.assertEqual(4, self.item.get("priority"))
        self.assertEqual(2, len(self.item.get("groups")))

        group = self.item.get("groups")[0]
        self.assertTrue(group)
        self.assertEqual("root", group.get("id"))
        self.assertEqual("grpRole:SNEP", group.get("role"))
        self.assertEqual(1, len(group.get("refs")))
        self.assertEqual("main", group.get("refs")[0].get("idRef"))

        group = self.item.get("groups")[1]
        self.assertEqual(10, len(group.get("refs")))
        self.assertEqual("main", group.get("id"))

        ref = group.get("refs")[0]
        self.assertTrue(ref)
        self.assertEqual("tag:reuters.com,0000:newsml_BRE9220HA:15", ref.get("residRef"))
        self.assertEqual("application/vnd.iptc.g2.packageitem+xml", ref.get("contentType"))
        self.assertEqual("icls:composite", ref.get("itemClass"))
        self.assertEqual("At least 15 killed on Kenya coast on election day", ref.get("headline"))
