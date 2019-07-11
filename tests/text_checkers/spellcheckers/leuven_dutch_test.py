# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import responses
from flask import Flask
from superdesk.tests import TestCase
from superdesk.text_checkers.spellcheckers.base import registered_spellcheckers
from superdesk.text_checkers import spellcheckers
from superdesk.text_checkers.spellcheckers.leuven_dutch import LeuvenDutch, API_URL, OPT_API_KEY
from superdesk import get_resource_service

spellcheckers.AUTO_IMPORT = False


@responses.activate
def load_spellcheckers():
    registered_spellcheckers.clear()
    app = Flask(__name__)
    app.config[OPT_API_KEY] = '123-456-789-ABC'
    spellcheckers.importSpellcheckers(app, spellcheckers.__name__)


class LeuvenDutchTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_spellcheckers()

    def test_list(self):
        """Check that Leuven Dutch spellchecker is listed by spellcheckers_list service"""
        doc = {}
        spellcheckers_list = get_resource_service('spellcheckers_list')
        spellcheckers_list.on_fetched(doc)
        for checker in doc['spellcheckers']:
            if ((checker['name'] == LeuvenDutch.name
                 and 'label' in checker
                 and set(checker['capacities']) == set(LeuvenDutch.capacities)
                 and checker['languages'] == ['nl'])):
                return
        self.fail("Leuven University Dutch spellchecker not found")

    @responses.activate
    def test_checker(self):
        """Check that spellchecking is working"""
        doc = {
            "spellchecker": LeuvenDutch.name,
            "text": "Outo rijden is gevaarlijk",
            "suggestions": False,
        }
        spellchecker = get_resource_service('spellchecker')
        check_url = API_URL.format(method="spellingchecker")
        responses.add(
            responses.POST, check_url,
            json={
                "status": {
                    "message": "ok",
                    "code": 200
                },
                "settings": {
                    "startmarker": "##__ERR_START__##",
                    "endmarker": "##__ERR_END__##",
                    "html": False
                },
                "spellingchecker": {
                    "input": "Outo rijden is gevaarlijk",
                    "output": {
                        "context": [
                            ""
                        ],
                        "mistakes": [
                            "Outo"
                        ],
                        "marked": "##__ERR_START__##Outo##__ERR_END__## rijden is gevaarlijk"
                    }
                },
                "debug": {
                    "timeneeded": 0.1197
                }
            }
        )
        spellchecker.create([doc])

        self.assertEqual(doc, {
            'errors': [{
                'json': {
                    'debug': {'timeneeded': 0.1197},
                    'settings': {
                        'endmarker': '##__ERR_END__##',
                        'html': False,
                        'startmarker': '##__ERR_START__##'},
                    'spellingchecker': {
                        'input': 'Outo rijden is gevaarlijk',
                        'output': {
                            'context': [''],
                            'marked': '##__ERR_START__##Outo##__ERR_END__## '
                            'rijden is '
                            'gevaarlijk',
                            'mistakes': ['Outo']}},
                    'status': {'code': 200, 'message': 'ok'}},
                'startOffset': 0,
                'text': 'Outo',
                'type': 'spelling'}],
            'spellchecker': 'leuven_dutch',
            'suggestions': False,
            'text': 'Outo rijden is gevaarlijk'})

    @responses.activate
    def test_suggest(self):
        """Check that spelling suggestions are working"""

        doc = {
            "spellchecker": "leuven_dutch",
            "text": "Outo",
            "suggestions": True
        }
        spellchecker = get_resource_service('spellchecker')
        check_url = API_URL.format(method="suggesties")
        responses.add(
            responses.POST, check_url,
            json={
                "status": {
                    "message": "ok",
                    "code": 200
                },
                "suggesties": {
                    "input": "Outo",
                    "output": {
                        "suggesties": [
                            "Otto",
                            "Buto",
                            "Kato",
                            "Cato",
                            "Lato",
                            "Leto",
                            "Curto",
                            "Mato",
                            "Beto",
                            "Busto"
                        ]
                    }
                },
                "debug": {
                    "timeneeded": 0.0861
                }
            }
        )
        spellchecker.create([doc])

        self.assertEqual(doc, {
            'spellchecker': 'leuven_dutch',
            'suggestions': [{'text': 'Otto'},
                            {'text': 'Buto'},
                            {'text': 'Kato'},
                            {'text': 'Cato'},
                            {'text': 'Lato'},
                            {'text': 'Leto'},
                            {'text': 'Curto'},
                            {'text': 'Mato'},
                            {'text': 'Beto'},
                            {'text': 'Busto'}],
            'text': 'Outo'})
