# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
import re
import datetime
import unittest
from pytz import utc

from superdesk.etree import etree
from superdesk.io.feed_parsers.afp_newsml_1_2_new import AFPNewsMLFeedParser


class TestCase(unittest.TestCase):
    def setUp(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.join(dirname, "../fixtures", "afp20.xml")
        provider = {"name": "Test"}
        with open(fixture, "rb") as f:
            self.item = AFPNewsMLFeedParser().parse(etree.fromstring(f.read()), provider)

    def test_headline(self):
        self.assertEqual(
            self.item.get("headline"), "DÃ©cÃ¨s de Naomi Musenga: l'opÃ©ratrice du Samu dÃ©finitivement condamnÃ©e"
        )

    def test_dateline(self):
        self.assertEqual(self.item.get("dateline", {}).get("text"), "Strasbourg, 10 juil 2024 (AFP)")

    def test_slugline(self):
        self.assertEqual(self.item.get("slugline"), "procÃ¨s-santÃ©-secours")

    def test_byline(self):
        self.assertEqual(self.item.get("byline"), "")

    def test_language(self):
        self.assertEqual(self.item.get("language"), "fr")

    def test_guid(self):
        self.assertEqual(self.item.get("guid"), "urn:newsml:afp.com:20240710:240710125902.qpsp2jzk:1")

    def test_coreitemvalues(self):
        self.assertEqual(self.item.get("type"), "text")
        self.assertEqual(self.item.get("urgency"), None)
        self.assertEqual(self.item.get("version"), "1")
        self.assertEqual(self.item.get("versioncreated"), datetime.datetime(2024, 7, 10, 12, 59, 2, tzinfo=utc))
        self.assertEqual(self.item.get("firstcreated"), datetime.datetime(2024, 7, 10, 12, 59, 2, tzinfo=utc))
        self.assertEqual(self.item.get("pubstatus"), "usable")

    def test_body_content(self):
        expected_output = (
            "<p>L'opÃ©ratrice du Samu condamnÃ©e pour non-assistance Ã personne en danger aprÃ¨s avoir raillÃ©"
            " au tÃ©lÃ©phone Naomi Musenga, jeune femme de 22 ans dÃ©cÃ©dÃ©e peu aprÃ¨s Ã l'hÃ´pital, a dÃ©cidÃ© "
            "de ne pas faire appel, s'est fÃ©licitÃ© mercredi l'avocat de la famille Musenga., avait Ã©tÃ© condamnÃ©e "
            "Ã un an de prison avec sursis, le 4 juillet, par le tribunal correctionnel de Strasbourg. ContactÃ© par l'AFP, "
            "le cabinet d'avocats de Me Thomas Callen, qui la dÃ©fendait, a confirmÃ© qu'elle n'interjetterait pas appel de cette "
            "condamnation.</p> <p>L'opÃ©ratrice, Corinne M.</p>"
        )
        actual_output = re.sub(r"\s+", " ", self.item.get("body_html")).strip()
        self.assertIn(expected_output, actual_output)
