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
from .utils import mock_dictionaries
import responses
from flask import Flask
from superdesk.tests import TestCase
from superdesk.text_checkers import tools
from superdesk.text_checkers.spellcheckers.base import registered_spellcheckers, SpellcheckerBase
from superdesk.text_checkers import spellcheckers
from superdesk.text_checkers.spellcheckers.languagetool import Languagetool, API_URL, OPT_API_KEY
from superdesk import get_resource_service

MODEL = {
    "misstake": 1,
}


@responses.activate
def load_spellcheckers():
    registered_spellcheckers.clear()
    app = Flask(__name__)
    app.config[OPT_API_KEY] = ""
    app.config[API_URL] = "https://api.languagetoolplus.com/v2/check"
    tools.import_services(app, spellcheckers.__name__, SpellcheckerBase)


class LanguagetoolTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_spellcheckers()

    def test_list(self):
        """Check that Languagetool spellchecker is listed by spellcheckers_list service"""
        doc = {}
        spellcheckers_list = get_resource_service("spellcheckers_list")
        spellcheckers_list.on_fetched(doc)
        for checker in doc["spellcheckers"]:
            if (
                checker["name"] == Languagetool.name
                and "label" in checker
                and set(checker["capacities"]) == set(Languagetool.capacities)
                and checker["languages"] == ["*"]
            ):
                return
        self.fail("Languagetool spellchecker not found")

    @responses.activate
    def test_checker(self, expected=None, use_internal_dict=False):
        """Check that spellchecking is working

        :param expected: "errors" expected
            to be specified if this test is re-used
        :param use_internal_dict: value to use in request
            can be changed if this test is re-used
        """
        doc = {
            "spellchecker": Languagetool.name,
            "text": "This is a simple text with a speling mistake.",
            "suggestions": False,
            "use_internal_dict": use_internal_dict,
        }
        spellchecker = get_resource_service("spellchecker")
        check_url = self.config.get(API_URL)
        responses.add(
            responses.POST,
            check_url,
            json={
                "software": {
                    "name": "LanguageTool", "version": "6.5.9", "apiVersion": 1, "premium": True, "status": ""
                },
                "warnings": {"incompleteResults": False},
                "language": {
                    "name": "English (US)", "code": "en-US", "detectedLanguage": {"name": "English (US)", "code": "en-US", "confidence": 1.0, "source": "ngram"}
                },
                "matches": [
                    {
                        "message": "Possible spelling mistake found.",
                        "shortMessage": "Spelling mistake",
                        "replacements": [
                            {"value": "spelling"},
                            {"value": "spewing"},
                            {"value": "spieling"}
                        ],
                        "offset": 29,
                        "length": 7,
                        "context": {
                            "text": "This is a simple text with a speling mistake.",
                            "offset": 29,
                            "length": 7
                        },
                        "sentence": "This is a simple text with a speling mistake.",
                        "type": {"typeName": "UnknownWord"},
                        "rule": {
                            "id": "MORFOLOGIK_RULE_EN_US",
                            "description": "Possible spelling mistake",
                            "issueType": "misspelling",
                            "category": {"id": "TYPOS", "name": "Possible Typo"},
                            "isPremium": False, "confidence": 0.68
                        },
                        "ignoreForIncompleteSentence": False, "contextForSureMatch": 0
                    }
                ],
                "sentenceRanges": [
                    [0, 45]
                ],
                "extendedSentenceRanges": [
                    {
                        "from": 0, "to": 45, "detectedLanguages": [
                            {"language": "en", "rate": 1.0}
                        ]
                    }
                ]
            },
        )
        spellchecker.create([doc])

        if expected is None:
            expected = [
                {
                    "message": "Possible spelling mistake found.",
                    "startOffset": 29,
                    "suggestions": [
                        {"text": "spelling"},
                        {"text": "spewing"},
                        {"text": "spieling"}
                    ],
                    "text": "speling",
                    "type": "spelling"
                }
            ]

        self.assertEqual(doc["errors"], expected)

    @patch("superdesk.get_resource_service", MagicMock(side_effect=partial(mock_dictionaries, model=MODEL)))
    def test_checker_with_internal_dict(self):
        """Check that words in personal dictionary are discarded correctly

        This test re-uses test_checker but activate "use_internal_dict" option and mock dictionary to have "misstake" inside
        """
        # misstake is in personal dictionary, so no spelling error should be returned
        expected = []
        self.test_checker(expected=expected, use_internal_dict=True)

    @responses.activate
    def test_suggest(self):
        """Check that spelling suggestions are working"""

        doc = {"spellchecker": "languagetool", "text": "misstake", "suggestions": True}
        spellchecker = get_resource_service("spellchecker")
        check_url = self.config.get(API_URL)
        responses.add(
            responses.POST,
            check_url,
            json={
                "software": {"name": "LanguageTool", "version": "6.5.9", "apiVersion": 1, "status": ""},
                "warnings": {"incompleteResults": False},
                "language": {
                    "name": "English (US)",
                    "code": "en-US",
                    "detectedLanguage": {"name": "English (US)", "code": "en-US", "confidence": 0.56296706, "source": "ngram"}
                },
                "matches": [
                    {
                        "message": "Possible spelling mistake found.",
                        "shortMessage": "Spelling mistake",
                        "replacements": [
                            {"value": "mistake"},
                            {"value": "misstate"},
                            {"value": "miss take"}
                        ],
                        "offset": 0,
                        "length": 8,
                        "context": {"text": "misstake", "offset": 0, "length": 8},
                        "sentence": "misstake",
                        "type": {"typeName": "UnknownWord"},
                        "rule": {
                            "id": "MORFOLOGIK_RULE_EN_US",
                            "description": "Possible spelling mistake",
                            "issueType": "misspelling",
                            "category": {"id": "TYPOS", "name": "Possible Typo"},
                            "isPremium": False, "confidence": 0.68
                        },
                        "ignoreForIncompleteSentence": False,
                        "contextForSureMatch": 0
                    }
                ],
                "sentenceRanges": [[0, 8]],
                "extendedSentenceRanges": [{"from": 0, "to": 8, "detectedLanguages": [{"language": "en", "rate": 1.0}]}]
            },
        )
        spellchecker.create([doc])

        self.assertEqual(
            doc,
            {
                "spellchecker": "languagetool",
                "suggestions": [
                    {"text": "mistake"},
                    {"text": "misstate"},
                    {"text": "miss take"},
                ],
                "text": "misstake",
            },
        )
