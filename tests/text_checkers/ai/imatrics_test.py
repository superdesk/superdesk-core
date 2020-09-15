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
from superdesk.errors import SuperdeskApiError
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
    def test_autotagging(self):
        """Check that autotagging is working"""
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

    @responses.activate
    def test_search(self):
        """Tag searching is returning tags"""
        doc = {
            "service": "imatrics",
            "operation": "search",
            "data": {"term": "informasjons"},
        }
        ai_data_op_service = get_resource_service('ai_data_op')
        api_url = urljoin(TEST_BASE_URL, "concept/get")
        responses.add(
            responses.POST, api_url,
            json={
                "result": [
                    {
                        "longDescription": "",
                        "pubStatus": True,
                        "aliases": [],
                        "latestVersionTimestamp": "2020-07-14T15:26:26Z",
                        "author": "NTB",
                        "createdTimestamp": "2020-07-14T15:26:26Z",
                        "shortDescription": "",
                        "broader": "",
                        "title": "informasjons- og kommunikasjonsteknologi",
                        "type": "category",
                        "uuid": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f"
                    },
                    {
                        "longDescription": "",
                        "pubStatus": True,
                        "aliases": [],
                        "latestVersionTimestamp": "2020-07-14T15:26:24Z",
                        "author": "NTB",
                        "createdTimestamp": "2020-07-14T15:26:24Z",
                        "shortDescription": "",
                        "broader": "",
                        "title": "informasjonsvitenskap",
                        "type": "category",
                        "uuid": "af815add-8456-3226-8177-ea0d8e3011eb"
                    }
                ],
                "response": "Request successful.",
                "error": False,
                "scrollID": "9e7da4cf-541f-36b1-b7a0-aa883a76c04f"
            }
        )
        ai_data_op_service.create([doc])

        expected = {
            'tags': [{'media_topics': [],
                      'title': 'informasjons- og kommunikasjonsteknologi',
                      'type': 'subject',
                      'uuid': 'c8a83204-29e0-3a7f-9a0e-51e76d885f7f',
                      'source': 'NTB',

                      },
                     {'media_topics': [],
                      'title': 'informasjonsvitenskap',
                      'type': 'subject',
                      'uuid': 'af815add-8456-3226-8177-ea0d8e3011eb',
                      'source': 'NTB',
                      }]
        }

        self.assertEqual(doc['result'], expected)

    @responses.activate
    def test_create(self):
        """Tag can be created"""
        doc = {
            "service": "imatrics",
            "operation": "create",
            "data": {"title": "test_create"},
        }
        ai_data_op_service = get_resource_service('ai_data_op')
        api_url = urljoin(TEST_BASE_URL, "concept/create")
        responses.add(
            responses.POST, api_url,
            json={
                'response': 'Concept created with uuid: 6083cb74-77b7-3046-8187-a6333b76b5a4.',
                "error": False
            }
        )
        ai_data_op_service.create([doc])
        self.assertEqual(doc['result'], {})

    @responses.activate
    def test_create_fail(self):
        """Tag creation conflict report raise an error"""
        doc = {
            "service": "imatrics",
            "operation": "create",
            "data": {"title": "test_create"},
        }
        ai_data_op_service = get_resource_service('ai_data_op')
        api_url = urljoin(TEST_BASE_URL, "concept/create")
        responses.add(
            responses.POST, api_url,
            json={
                "response": "A concept of type topic and title test_create already exists with uuid a2d0ce94-e4b2-3102-"
                            "9671-9307b464573c.",
                "error": True
            }
        )
        with self.assertRaises(SuperdeskApiError) as cm:
            ai_data_op_service.create([doc])

        exc = cm.exception
        self.assertEqual(exc.status_code, 502)

    @responses.activate
    def test_delete(self):
        """Tag can be deleted"""
        doc = {
            "service": "imatrics",
            "operation": "delete",
            "data": {"uuid": "afc7e49d-57d0-34af-b184-b7600af362a9"},
        }
        ai_data_op_service = get_resource_service('ai_data_op')
        api_url = urljoin(TEST_BASE_URL, "concept/delete") + "?uuid=afc7e49d-57d0-34af-b184-b7600af362a9"
        responses.add(
            responses.DELETE, api_url,
            body="Concept deleted",
        )
        ai_data_op_service.create([doc])

        self.assertEqual(doc['result'], {})
