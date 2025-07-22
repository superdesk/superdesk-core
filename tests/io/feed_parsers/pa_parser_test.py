# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from datetime import datetime
from superdesk.utc import utc
from superdesk.etree import etree
from superdesk.tests import TestCase
from superdesk.io.feed_parsers.pa_parser import PAParser


class PAParserTestCase(TestCase):
    """
    Test case for the PA NewsML Parser.
    """

    def setUp(self):
        super().setUp()
        self.dirname = os.path.dirname(os.path.realpath(__file__))
        self.fixture = os.path.normpath(os.path.join(self.dirname, "../fixtures/pa_parser.xml"))
        self.provider = {"name": "Test"}
        with open(self.fixture, "rb") as f:
            xml = etree.parse(f)
            self.item = PAParser().parse(xml.getroot(), self.provider)

    def test_headline(self):
        """
        Test if the headline is correctly parsed.
        """
        self.assertEqual(self.item.get("headline"), "EDINBURGH FESTIVAL FRINGE PROGRAMME LAUNCHED")

    def test_byline(self):
        """
        Test if the byline is correctly parsed.
        """
        self.assertEqual(self.item.get("byline"), "By Sarah Ward, PA Scotland")

    def test_slugline(self):
        """
        Test if the slugline is correctly parsed.
        """
        self.assertEqual(self.item.get("slugline"), "ARTS Fringe")

    def test_versioncreated(self):
        """
        Test if the versioncreated timestamp is correctly parsed.
        """
        expected = datetime(2025, 6, 2, 10, 46, 50, tzinfo=utc)
        self.assertEqual(self.item.get("versioncreated"), expected)

    def test_firstcreated(self):
        """
        Test if the firstcreated timestamp is correctly parsed.
        """
        expected = datetime(2025, 6, 2, 10, 46, 50, tzinfo=utc)
        self.assertEqual(self.item.get("firstcreated"), expected)

    def test_guid(self):
        """
        Test if the guid is correctly parsed.
        """
        self.assertEqual(self.item.get("guid"), "urn:newsml:pa.press.net:20250602:PA-HHH-ARTS-Fringe:11839114654855")

    def test_priority(self):
        """
        Test if the priority is correctly parsed.
        """
        self.assertEqual(self.item.get("priority"), 4)

    def test_urgency(self):
        """
        Test if the urgency is correctly parsed.
        """
        self.assertEqual(self.item.get("urgency"), 4)

    def test_subjects(self):
        """
        Test if subjects are correctly parsed.
        """
        subjects = self.item.get("subject", [])
        self.assertEqual(len(subjects), 2)
        self.assertIn({"name": "ARTS", "qcode": "ARTS", "scheme": "topics"}, subjects)
        self.assertIn({"name": "SCOTLAND", "qcode": "SCOTLAND", "scheme": "topics"}, subjects)

    def test_keywords(self):
        """
        Test if the keywords are correctly parsed.
        """
        self.assertEqual(self.item.get("keywords"), ["Fringe"])

    def test_copyright(self):
        """
        Test if copyright notice is correctly parsed.
        """
        self.assertEqual(self.item.get("copyrightnotice"), "Press Association")

    def test_body_html(self):
        """
        Test if the body HTML is correctly parsed.
        """
        body_html = self.item.get("body_html")
        self.assertTrue(body_html.startswith("<p>The programme for the Edinburgh Festival Fringe has been launched"))
        self.assertIn("<p>Topics include the apocalypse, rave culture, disability and sexuality", body_html)
        # Test that inline tags were stripped but content remains
        self.assertIn("August 1 to 25", body_html)
        self.assertIn("Hibernian Football Club's", body_html)
        self.assertNotIn("<chron>", body_html)
        self.assertNotIn("<org>", body_html)

    def test_custom_tags_stripped_from_body(self):
        """
        Test that custom tags are stripped from body_html.
        """
        body_html = self.item.get("body_html")
        self.assertNotIn("<chron>", body_html)
        self.assertNotIn("</chron>", body_html)
        self.assertNotIn("<org>", body_html)
        self.assertNotIn("</org>", body_html)
        self.assertNotIn("<person>", body_html)
        self.assertNotIn("</person>", body_html)
        self.assertNotIn("<location>", body_html)
        self.assertNotIn("</location>", body_html)

    def test_embargo(self):
        """
        Test if embargo is correctly parsed.
        """
        self.assertTrue("embargo" in self.item)

    def test_original_source(self):
        """
        Test if original source is correctly parsed.
        """
        self.assertEqual(self.item.get("original_source"), "The Press Association")

    def test_pubstatus(self):
        """
        Test if pubstatus is correctly parsed.
        """
        self.assertEqual(self.item.get("pubstatus"), "embargoed")
