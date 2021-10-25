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
from lxml import etree
from superdesk.io.feed_parsers.scoop_newsml_2_0 import ScoopNewsMLTwoFeedParser
from superdesk.tests import TestCase


class ScoopTestCase(TestCase):
    filename = "scoop.xml"
    vocab = [
        {
            "_id": "locators",
            "items": [
                {
                    "is_active": True,
                    "name": "NZ",
                    "world_region": "Oceania",
                    "country": "New Zealand",
                    "state": "",
                    "qcode": "NZ",
                    "group": "Rest Of World",
                }
            ],
        }
    ]

    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with self.app.app_context():
            self.app.data.insert("vocabularies", self.vocab)
        with open(fixture, "rb") as f:
            parser = ScoopNewsMLTwoFeedParser()
            self.xml = etree.parse(f)
            self.item = parser.parse(self.xml.getroot(), provider)

    def test_content(self):
        self.assertEqual(
            self.item[0].get("headline"),
            "Dick Smith receivers install Don Grover as acting CEO as Abboud " + "quits; retailer put up for sale",
        )
        self.assertEqual(self.item[0].get("guid"), "BD-20160112123540:3")
        self.assertEqual(self.item[0].get("uri"), "BD-20160112123540")
        self.assertEqual(self.item[0].get("priority"), 6)
        self.assertEqual(self.item[0].get("version"), "3")
        self.assertEqual(self.item[0].get("firstcreated").isoformat(), "2016-01-11T23:35:40+00:00")
        self.assertEqual(self.item[0].get("urgency"), 3)
        self.assertTrue(self.item[0].get("body_html").startswith("<p>The receivers of Dick Smith Holdings"))
        self.assertEqual(self.item[0].get("byline"), "Jonathan Underhill")
        self.assertEqual(self.item[0].get("dateline").get("located").get("city"), "Wellington")
        self.assertEqual(self.item[0].get("place")[0].get("name"), "NZ")

    def test_can_parse(self):
        self.assertTrue(ScoopNewsMLTwoFeedParser().can_parse(self.xml.getroot()))
