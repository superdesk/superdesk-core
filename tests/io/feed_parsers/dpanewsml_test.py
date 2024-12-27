# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import datetime
import os
from superdesk.tests import TestCase
from pytz import utc

from superdesk.etree import etree
from superdesk.io.feed_parsers.dpa_newsml import DPAFeedParser


class DPANewsMLTestCase(TestCase):
    parser = DPAFeedParser()

    filename = "dpa.xml"

    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with open(fixture, "rb") as f:
            self.nitf = f.read()
            self.item = self.parser.parse(etree.fromstring(self.nitf), provider)[0]

    def test_headline(self):
        with self.app.app_context():
            self.assertEqual(
                self.item.get("headline"), "Eintracht in London: Hintereggers Tränen und Attacke auf Reporter"
            )

    def test_slugline(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("slugline"), "")

    def test_byline(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("byline"), None)

    def test_language(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("language"), "de")

    def test_guid(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("guid"), "urn:newsml:dpa.com:20090101:221011-930-4303:1")

    def test_coreitemvalues(self):
        with self.app.app_context():
            print(self.item)
            self.assertEqual(self.item.get("type"), "text")
            self.assertEqual(self.item.get("urgency"), 4)
            self.assertEqual(self.item.get("version"), "1")
            self.assertEqual(self.item.get("versioncreated"), datetime.datetime(2022, 10, 11, 9, 14, 42, tzinfo=utc))
            self.assertEqual(self.item.get("firstcreated"), None)
            self.assertEqual(self.item.get("pubstatus"), "usable")

    def test_uri(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("uri"), "urn:newsml:dpa.com:20090101:221011-930-4303")

    def test_authors(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("authors"), [{"uri": None, "name": "degenhardt.sandra"}])

    def test_usageterms(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("usageterms"), "Nutzung nur nach schriftlicher Vereinbarung mit dpa")

    def test_renditions(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("renditions"), {})

    def test_word_count(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("word_count"), 226)

    def test_body_html(self):
        with self.app.app_context():
            self.assertIsInstance(self.item.get("body_html"), type(""))
            self.assertEqual(self.item.get("body_html"), "<header>  </header>")

    def test_priority(self):
        with self.app.app_context():
            self.assertEqual(self.item.get("priority"), 5)
