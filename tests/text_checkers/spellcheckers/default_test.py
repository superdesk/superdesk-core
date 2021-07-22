# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from functools import partial
from unittest.mock import MagicMock, patch
from flask import Flask
from .utils import mock_dictionaries
from superdesk.tests import TestCase
from superdesk.text_checkers import tools
from superdesk.text_checkers import spellcheckers
from superdesk.text_checkers.spellcheckers import SPELLCHECKER_DEFAULT
from superdesk.text_checkers.spellcheckers.base import registered_spellcheckers, SpellcheckerBase
from superdesk.text_checkers.spellcheckers.default import Default
from superdesk import get_resource_service

spellcheckers.AUTO_IMPORT = False


MODEL = {
    "is": 1,
    "there": 1,
    "a": 1,
    "spelling": 1,
    "mistake": 1,
    "number": 1,
    "rendez-vous": 1,
    "this": 1,
    "are": 1,
    "proper": 1,
    "nouns": 1,
}


def load_spellcheckers():
    registered_spellcheckers.clear()
    app = Flask(__name__)
    tools.import_services(app, spellcheckers.__name__, SpellcheckerBase)


class DefaultSpellcheckerTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_spellcheckers()

    def test_list(self):
        """Check that Default spellchecker is listed by spellcheckers_list service"""
        doc = {}
        spellcheckers_list = get_resource_service("spellcheckers_list")
        spellcheckers_list.on_fetched(doc)
        for checker in doc["spellcheckers"]:
            if (
                checker["name"] == SPELLCHECKER_DEFAULT
                and "label" in checker
                and set(checker["capacities"]) == set(Default.capacities)
                and checker["languages"] == ["*"]
            ):
                return
        self.fail("Defaut spellchecker not found")

    @patch("superdesk.get_resource_service", MagicMock(side_effect=partial(mock_dictionaries, model=MODEL)))
    def test_checker(self):
        """Check that spellchecking is working"""
        doc = {
            "spellchecker": "default",
            # the number is to test that they are not seen as mistakes
            # and the "rendez-vous" is to check that compound words work
            "text": "Is therre a speling mitake? A number: 123456, a rendez-vous",
            "suggestions": False,
            "language": "en",
            "use_internal_dict": False,
        }
        spellchecker = get_resource_service("spellchecker")
        spellchecker.create([doc])

        self.assertEqual(
            doc["errors"],
            [
                {"startOffset": 3, "text": "therre", "type": "spelling"},
                {"startOffset": 12, "text": "speling", "type": "spelling"},
                {"startOffset": 20, "text": "mitake", "type": "spelling"},
            ],
        )

    @patch("superdesk.get_resource_service", MagicMock(side_effect=partial(mock_dictionaries, model=MODEL)))
    def test_suggest(self):
        """Check that spelling suggestions are working"""

        doc = {
            "spellchecker": "default",
            "text": "mitake",
            "suggestions": True,
            "language": "en",
        }
        spellchecker = get_resource_service("spellchecker")
        spellchecker.create([doc])

        self.assertEqual(
            doc,
            {
                "language": "en",
                "spellchecker": "default",
                "suggestions": [{"text": "mistake"}, {"text": "Mistake"}],
                "text": "mitake",
            },
        )

    @patch("superdesk.get_resource_service", MagicMock(side_effect=partial(mock_dictionaries, model=MODEL)))
    def test_ignore(self):
        """Check that "ignore" is working (SDBELGA-165)"""
        doc = {
            "spellchecker": "default",
            "text": "This is are proper nouns: David, Jean, Arthur",
            "suggestions": False,
            "language": "en",
            "use_internal_dict": False,
        }
        spellchecker = get_resource_service("spellchecker")
        spellchecker.create([doc])

        self.assertEqual(
            doc["errors"],
            [
                {"startOffset": 26, "text": "David", "type": "spelling"},
                {"startOffset": 33, "text": "Jean", "type": "spelling"},
                {"startOffset": 39, "text": "Arthur", "type": "spelling"},
            ],
        )

        # now the same check with ignore
        doc = doc.copy()
        doc["ignore"] = ["David", "Jean", "Arthur"]
        spellchecker.create([doc])

        self.assertEqual(doc["errors"], [])
