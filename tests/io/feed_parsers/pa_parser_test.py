#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024, Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from superdesk.tests import TestCase
from superdesk.io.feed_parsers.pa_parser import PAParser
from superdesk.etree import etree


class PAParserTestCase(TestCase):
    """
    Test case for the PA Parser.
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
        self.assertEqual(
            self.item.get("headline"),
            "MORE THAN FOUR IN FIVE SCHOOL LEADERS ABUSED BY PARENTS IN PAST YEAR - SURVEY",
        )

    def test_byline(self):
        """
        Test if the byline is correctly parsed.
        """
        self.assertEqual(
            self.item.get("byline"),
            "By Eleanor Busby, PA Education Correspondent",
        )

    def test_versioncreated(self):
        """
        Test if the versioncreated timestamp is correctly parsed.
        """
        self.assertEqual(
            self.item.get("versioncreated").isoformat(),
            "2025-03-04T00:01:00+00:00",
        )

    def test_firstcreated(self):
        """
        Test if the firstcreated timestamp is correctly parsed.
        """
        self.assertEqual(
            self.item.get("firstcreated").isoformat(),
            "2025-03-03T02:45:45+00:00",
        )

    def test_abstract(self):
        """
        Test if the abstract is correctly parsed.
        """
        self.assertEqual(
            self.item.get("abstract"),
            "The majority of school leaders have reported being abused by parents in the past year, a survey has suggested.",
        )

    def test_keywords(self):
        """
        Test if the keywords are correctly parsed.
        """
        self.assertIn("EDUCATION", self.item.get("keywords"))

    def test_word_count(self):
        """
        Test if the word count is correctly parsed.
        """
        self.assertEqual(self.item.get("word_count"), 749)

    def test_body_html(self):
        """
        Test if the body HTML is correctly parsed.
        """
        body_html = self.item.get("body_html")
        self.assertTrue(body_html.startswith("<p>The majority of school leaders have reported being abused by parents"))
        self.assertIn("<p>More than two in five school leaders (42%)", body_html)
        self.assertIn("<p>One in 10 school leaders said they had suffered physical violence", body_html)

    def test_usageterms(self):
        """
        Test if the usage terms (copyright) are correctly parsed.
        """
        self.assertEqual(
            self.item.get("usageterms"),
            "Press Association 2025",
        )
