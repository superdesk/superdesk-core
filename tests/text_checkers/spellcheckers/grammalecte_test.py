# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from urllib.parse import urljoin
import responses
from flask import Flask
from superdesk.tests import TestCase
from superdesk.text_checkers import tools
from superdesk.text_checkers import spellcheckers
from superdesk.text_checkers.spellcheckers.base import registered_spellcheckers, SpellcheckerBase
from superdesk.text_checkers.spellcheckers.grammalecte import PATH_CHECK, PATH_SUGGEST, Grammalecte
from superdesk import get_resource_service
import os

spellcheckers.AUTO_IMPORT = False

TEST_URL = "http://localhost:8080"
os.environ["GRAMMALECTE_URL"] = TEST_URL


@responses.activate
def load_spellcheckers():
    """Load spellcheckers by mocking Grammalecte server, so it can be detected"""
    registered_spellcheckers.clear()
    app = Flask(__name__)
    check_url = urljoin(TEST_URL, PATH_CHECK)
    responses.add(
        responses.POST,
        check_url,
        json={
            "program": "grammalecte-fr",
            "version": "1.2",
        },
    )
    tools.import_services(app, spellcheckers.__name__, SpellcheckerBase)


class GrammalecteTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_spellcheckers()

    def test_list(self):
        """Check that Grammalecte is listed by spellcheckers_list service"""
        doc = {}
        spellcheckers_list = get_resource_service("spellcheckers_list")
        spellcheckers_list.on_fetched(doc)
        for checker in doc["spellcheckers"]:
            if (
                checker["name"] == Grammalecte.name
                and "label" in checker
                and set(checker["capacities"]) == set(Grammalecte.capacities)
                and checker["languages"] == ["fr"]
            ):
                return
        self.fail("Grammalecte not found")

    @responses.activate
    def test_checker(self):
        """Check that spellchecking is working"""
        doc = {
            "spellchecker": "grammalecte",
            "text": "Il nous reste à vérifié votre maquette.",
            "suggestions": False,
            "use_internal_dict": False,
        }
        spellchecker = get_resource_service("spellchecker")
        check_url = urljoin(TEST_URL, PATH_CHECK)
        responses.add(
            responses.POST,
            check_url,
            json={
                "program": "grammalecte-fr",
                "version": "1.2",
                "lang": "fr",
                "error": "",
                "data": [
                    {
                        "iParagraph": 1,
                        "lGrammarErrors": [
                            {
                                "nStart": 14,
                                "nEnd": 15,
                                "sLineId": "#5864",
                                "sRuleId": "conf_a_à_verbe__b13_a2_0",
                                "sType": "conf",
                                "aColor": [89, 49, 129],
                                "sMessage": "Confusion probable : “à” est une préposition. Pour le verbe “avoir”, écrivez “a”.",
                                "aSuggestions": ["a"],
                                "URL": "",
                            },
                            {
                                "nStart": 16,
                                "nEnd": 23,
                                "sLineId": "#5864",
                                "sRuleId": "conf_a_à_verbe__b13_a3_0",
                                "sType": "conf",
                                "aColor": [89, 49, 129],
                                "sMessage": "Le verbe devrait être à l’infinitif.",
                                "aSuggestions": ["vérifier"],
                                "URL": "",
                            },
                        ],
                        "lSpellingErrors": [],
                    }
                ],
            },
        )
        spellchecker.create([doc])

        expected = [
            {
                "startOffset": 14,
                "suggestions": [{"text": "a"}],
                "text": "à",
                "message": "Confusion probable : “à” est une préposition. " "Pour le verbe “avoir”, écrivez “a”.",
                "type": "grammar",
            },
            {
                "startOffset": 16,
                "suggestions": [{"text": "vérifier"}],
                "text": "vérifié",
                "message": "Le verbe devrait être à l’infinitif.",
                "type": "grammar",
            },
        ]

        self.assertEqual(doc["errors"], expected)

    @responses.activate
    def test_checker_paragraphs(self):
        """Check that spellchecking is working as expected with 2 paragraphs"""
        doc = {
            "spellchecker": "grammalecte",
            "text": "Il nous reste à vérifié votre maquette.\n\nIl nous reste à vérifié votre maquette.",
            "suggestions": False,
            "use_internal_dict": False,
        }
        spellchecker = get_resource_service("spellchecker")
        check_url = urljoin(TEST_URL, PATH_CHECK)
        responses.add(
            responses.POST,
            check_url,
            json={
                "program": "grammalecte-fr",
                "version": "1.1",
                "lang": "fr",
                "error": "",
                "data": [
                    {
                        "iParagraph": 1,
                        "lGrammarErrors": [
                            {
                                "URL": "",
                                "aColor": [89, 49, 129],
                                "aSuggestions": ["a"],
                                "nEnd": 15,
                                "nStart": 14,
                                "sLineId": "#5643",
                                "sMessage": "Confusion probable : “à” est une "
                                "préposition. Pour le verbe "
                                "“avoir”, écrivez “a”.",
                                "sRuleId": "conf_a_à_verbe__b13_a2_0",
                                "sType": "conf",
                            },
                            {
                                "URL": "",
                                "aColor": [89, 49, 129],
                                "aSuggestions": ["vérifier"],
                                "nEnd": 23,
                                "nStart": 16,
                                "sLineId": "#5643",
                                "sMessage": "Le verbe devrait être à " "l’infinitif.",
                                "sRuleId": "conf_a_à_verbe__b13_a3_0",
                                "sType": "conf",
                            },
                        ],
                        "lSpellingErrors": [],
                    },
                    {
                        "iParagraph": 3,
                        "lGrammarErrors": [
                            {
                                "URL": "",
                                "aColor": [89, 49, 129],
                                "aSuggestions": ["a"],
                                "nEnd": 15,
                                "nStart": 14,
                                "sLineId": "#5643",
                                "sMessage": "Confusion probable : “à” est une "
                                "préposition. Pour le verbe "
                                "“avoir”, écrivez “a”.",
                                "sRuleId": "conf_a_à_verbe__b13_a2_0",
                                "sType": "conf",
                            },
                            {
                                "URL": "",
                                "aColor": [89, 49, 129],
                                "aSuggestions": ["vérifier"],
                                "nEnd": 23,
                                "nStart": 16,
                                "sLineId": "#5643",
                                "sMessage": "Le verbe devrait être à " "l’infinitif.",
                                "sRuleId": "conf_a_à_verbe__b13_a3_0",
                                "sType": "conf",
                            },
                        ],
                        "lSpellingErrors": [],
                    },
                ],
            },
        )
        spellchecker.create([doc])

        expected = [
            {
                "message": "Confusion probable : “à” est une préposition. Pour le " "verbe “avoir”, écrivez “a”.",
                "startOffset": 14,
                "suggestions": [{"text": "a"}],
                "text": "à",
                "type": "grammar",
            },
            {
                "message": "Le verbe devrait être à l’infinitif.",
                "startOffset": 16,
                "suggestions": [{"text": "vérifier"}],
                "text": "vérifié",
                "type": "grammar",
            },
            {
                "message": "Confusion probable : “à” est une préposition. Pour le " "verbe “avoir”, écrivez “a”.",
                "startOffset": 55,
                "suggestions": [{"text": "a"}],
                "text": "à",
                "type": "grammar",
            },
            {
                "message": "Le verbe devrait être à l’infinitif.",
                "startOffset": 57,
                "suggestions": [{"text": "vérifier"}],
                "text": "vérifié",
                "type": "grammar",
            },
        ]

        self.assertEqual(doc["errors"], expected)

    @responses.activate
    def test_suggest(self):
        """Check that spelling suggestions are working"""

        doc = {
            "spellchecker": "grammalecte",
            "text": "fote",
            "suggestions": True,
        }
        spellchecker = get_resource_service("spellchecker")
        check_url = urljoin(TEST_URL, PATH_SUGGEST)
        responses.add(
            responses.POST,
            check_url,
            json={
                "suggestions": ["faute", "fauté", "féauté", "sotte", "rote", "roté", "note", "noté", "lote", "lotte"]
            },
        )
        spellchecker.create([doc])

        self.assertEqual(
            doc,
            {
                "spellchecker": "grammalecte",
                "suggestions": [
                    {"text": "faute"},
                    {"text": "fauté"},
                    {"text": "féauté"},
                    {"text": "sotte"},
                    {"text": "rote"},
                    {"text": "roté"},
                    {"text": "note"},
                    {"text": "noté"},
                    {"text": "lote"},
                    {"text": "lotte"},
                ],
                "text": "fote",
            },
        )
