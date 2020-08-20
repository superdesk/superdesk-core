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
from superdesk.text_checkers import ai
from superdesk.text_checkers.ai.base import registered_ai_services, AIServiceBase
from superdesk import get_resource_service

ai.AUTO_IMPORT = False
TEST_BASE_URL = "https://something.example.org"


@responses.activate
def load_ai_services():
    """Load ai servies by mocking Grammalecte server, so it can be detected"""
    registered_ai_services.clear()
    app = Flask(__name__)
    app.config["IMATRICS_BASE_URL"] = TEST_BASE_URL
    app.config["IMATRICS_USER"] = "some_user"
    app.config["IMATRICS_KEY"] = "some_secret_key"
    tools.import_services(app, ai.__name__, AIServiceBase)


class IMatricsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_ai_services()

    def setUp(self):
        with self.app.app_context():
            self.app.data.insert('archive', [
                {
                    "_id": "test_1",
                    "guid": "test_1",
                    "type": "text",
                    "version": 1,
                    "body_html": "<p>this is a fake article to test the imatrics service, it should be returning some "
                                 "interesting tags.</p>",
                    "headline": "test imatrics",
                    "slugline": "test imatrics",
                }
            ])

    @responses.activate
    def test_checker(self):
        """Check that spellchecking is working"""
        doc = {
            "service": "imatrics",
            "item_id": "test_1",
        }
        ai_service = get_resource_service('ai')
        api_url = urljoin(TEST_BASE_URL, "article/concept")
        responses.add(
            responses.POST, api_url,
            json=[
                {
                    "weight": 1,
                    "geometry": {},
                    "links": [],
                    "title": "IT",
                    "type": "topic",
                    "uuid": "e3c482c0-08a4-3b31-a7f1-e231f1ddffc4"
                },
                {
                    "weight": 0.8387794287831216,
                    "geometry": {},
                    "links": [],
                    "title": "Service",
                    "type": "topic",
                    "uuid": "44f52663-52f9-3836-ac45-ae862fe945a3"
                },
                {
                    "weight": 1,
                    "geometry": {},
                    "links": [
                        {
                            "relationType": "",
                            "id": "medtop:20000763",
                            "source": "IPTC",
                            "uri": "",
                            "url": ""
                        }
                    ],
                    "title": "informasjons- og kommunikasjonsteknologi",
                    "type": "category",
                    "uuid": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f"
                }
            ]

        )
        ai_service.create([doc])

        expected = {
            "subject": [
                {
                    "media_topics": [],
                    "title": "IT",
                    "uuid": "e3c482c0-08a4-3b31-a7f1-e231f1ddffc4",
                },
                {
                    "media_topics": [
                        {
                            "name": "informasjons- og kommunikasjonsteknologi",
                            "code": "20000763"
                        }
                    ],
                    "title": "informasjons- og kommunikasjonsteknologi",
                    "uuid": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                },
                {
                    "media_topics": [],
                    "title": "Service",
                    "uuid": "44f52663-52f9-3836-ac45-ae862fe945a3",
                }
            ]
        }

        self.assertEqual(doc['analysis'], expected)
