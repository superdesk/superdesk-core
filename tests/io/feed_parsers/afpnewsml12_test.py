# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import datetime
import os
import unittest
from pytz import utc

from superdesk.etree import etree
from superdesk.io.feed_parsers.afp_newsml_1_2 import AFPNewsMLOneFeedParser


class TestCase(unittest.TestCase):
    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.join(dirname, "../fixtures", "afp.xml")
        provider = {"name": "Test"}
        with open(fixture, "rb") as f:
            self.item = AFPNewsMLOneFeedParser().parse(etree.fromstring(f.read()), provider)

    def test_headline(self):
        self.assertEqual(self.item.get("headline"), "Sweden court accepts receivership for Saab carmaker")

    def test_dateline(self):
        self.assertEqual(self.item.get("dateline", {}).get("text"), "STOCKHOLM, Aug 29, 2014 (AFP) -")

    def test_slugline(self):
        self.assertEqual(self.item.get("slugline"), "Sweden-SAAB")

    def test_byline(self):
        self.assertEqual(self.item.get("byline"), "")

    def test_language(self):
        self.assertEqual(self.item.get("language"), "en")

    def test_guid(self):
        self.assertEqual(self.item.get("guid"), "urn:newsml:afp.com:20140829T135002Z:TX-PAR-FXW86:1")

    def test_coreitemvalues(self):
        self.assertEqual(self.item.get("type"), "text")
        self.assertEqual(self.item.get("urgency"), 4)
        self.assertEqual(self.item.get("version"), "1")
        self.assertEqual(self.item.get("versioncreated"), utc.localize(datetime.datetime(2014, 8, 29, 13, 49, 51)))
        self.assertEqual(self.item.get("firstcreated"), utc.localize(datetime.datetime(2014, 8, 29, 13, 49, 51)))
        self.assertEqual(self.item.get("pubstatus"), "usable")

    def test_subjects(self):
        self.assertEqual(len(self.item.get("subject")), 5)
        self.assertIn({"name": "automotive equipment", "qcode": "04011002"}, self.item.get("subject"))
        self.assertIn({"name": "bankruptcy", "qcode": "04016007"}, self.item.get("subject"))
        self.assertIn({"name": "economy, business and finance", "qcode": "04000000"}, self.item.get("subject"))
        self.assertIn(
            {"name": "quarterly or semiannual financial statement", "qcode": "04016038"}, self.item.get("subject")
        )
        self.assertIn({"name": "manufacturing and engineering", "qcode": "04011000"}, self.item.get("subject"))

    def test_usageterms(self):
        self.assertEqual(self.item.get("usageterms"), "NO ARCHIVAL USE")

    def test_genre(self):
        self.assertIn({"name": "business"}, self.item.get("genre"))
        self.assertIn({"name": "bankruptcy"}, self.item.get("genre"))

    def test_content_is_text(self):
        self.assertIsInstance(self.item.get("body_html"), type(""))
        self.assertNotRegex(self.item.get("body_html"), "<body.content>")
