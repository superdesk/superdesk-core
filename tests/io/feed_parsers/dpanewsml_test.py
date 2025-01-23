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

    async def asyncSetUp(self):
        await super().asyncSetUp()
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with open(fixture, "rb") as f:
            self.nitf = f.read()
            self.item = self.parser.parse(etree.fromstring(self.nitf), provider)[0]

    def test_headline(self):
        self.assertEqual(self.item.get("headline"), "Eintracht in London: Hintereggers Tränen und Attacke auf Reporter")

    def test_slugline(self):
        self.assertEqual(self.item.get("slugline"), "")

    def test_byline(self):
        self.assertEqual(self.item.get("byline"), None)

    def test_language(self):
        self.assertEqual(self.item.get("language"), "de")

    def test_guid(self):
        self.assertEqual(self.item.get("guid"), "urn:newsml:dpa.com:20090101:221011-930-4303:1")

    def test_coreitemvalues(self):
        self.assertEqual(self.item.get("type"), "text")
        self.assertEqual(self.item.get("urgency"), 4)
        self.assertEqual(self.item.get("version"), "1")
        self.assertEqual(self.item.get("versioncreated"), datetime.datetime(2022, 10, 11, 9, 14, 42, tzinfo=utc))
        self.assertEqual(self.item.get("firstcreated"), None)
        self.assertEqual(self.item.get("pubstatus"), "usable")

    def test_uri(self):
        self.assertEqual(self.item.get("uri"), "urn:newsml:dpa.com:20090101:221011-930-4303")

    def test_authors(self):
        self.assertEqual(self.item.get("authors"), [{"uri": None, "name": "degenhardt.sandra"}])

    def test_usageterms(self):
        self.assertEqual(self.item.get("usageterms"), "Nutzung nur nach schriftlicher Vereinbarung mit dpa")

    def test_renditions(self):
        self.assertEqual(self.item.get("renditions"), {})

    def test_word_count(self):
        self.assertEqual(self.item.get("word_count"), 226)

    def test_body_html(self):
        self.assertIsInstance(self.item.get("body_html"), str)
        expected_output = (
            '<p><span class="dateline">London <span class="credit">(dpa)'
            "</span> - </span>2019 gab es bittere Tränen in der Kurve"
            ", 2022 erst mächtig Wut auf englische Fans und eine Woche später ausgelassenen Jubel:"
            " Für Eintracht Frankfurt ist London in den vergangenen Jahren zu einem Standard-Reiseziel"
            " im europäischen Fußball-Wettbewerb geworden. Bevor es am Mittwochabend (21.00 Uhr/DAZN) "
            "bei Tottenham Hotspur um wichtige Punkte in der Champions League geht, wird sich die Reisegruppe "
            "um Torhüter Kevin Trapp und Routinier Makoto Hasebe bestimmt an die vergangenen London-Reisen erinnern."
            "</p><p>Beim Topclub FC Chelsea wollte die damals von Adi Hütter trainierte Eintracht in der Saison 2018/19 "
            "ihre Erfolgsserie fortsetzen und nach Inter Mailand und Schachtjor Donezk auch die «Blues» aus der Europa League werfen. "
            "Nach zwei 1:1 ging es an der Stamford Bridge in die Verlängerung und ins Elfmeterschießen. Der inzwischen abgetretene"
            " Martin Hinteregger vergab vom Punkt, vergoss nach dem bitteren Aus Tränen und wurde anschließend in der Fankurve getröstet."
            "</p><p>Sportlich weckt der 2:1-Erfolg im Halbfinal-Hinspiel bei West Ham United Ende April positive Erinnerungen "
            "- schließlich war er der Grundstein für den späteren Triumph in Sevilla. Doch eine Attacke von englischen Fans gegen "
            "zwei Journalisten des Hessischen Rundfunks trübte das Bild. Die Rundfunk-Reporter bekamen nach eigenen Angaben «mehrfach Faustschläge an den Hinterkopf"
            ", in den Nacken, in den Rücken». West Ham United machte die Täter später ausfindig. Eine Woche später gewann die Eintracht"
            " auch das Rückspiel und zog ins Endspiel ein.</p><p> </p>"
        )

        self.assertEqual(self.item.get("body_html").strip(), expected_output.strip())

    def test_priority(self):
        self.assertEqual(self.item.get("priority"), 5)

    def test_keywords(self):
        self.assertEqual(self.item.get("keywords"), ["Champions League", "Frankfurt", "London"])
