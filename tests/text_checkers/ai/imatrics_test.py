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
from urllib.parse import urljoin
from superdesk.tests import TestCase
from superdesk.text_checkers import tools
from superdesk.text_checkers import ai
from superdesk.text_checkers.ai.base import registered_ai_services, AIServiceBase
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service

ai.AUTO_IMPORT = False
TEST_BASE_URL = "https://something.example.org"


class IMatricsTestCase(TestCase):

    maxDiff = None

    item = {
        "_id": "test_1",
        "guid": "test_1",
        "type": "text",
        "version": 1,
        "language": "en",
        "body_html": "<p>this is a fake article to test the imatrics service, it should be returning some "
        "interesting tags.</p>",
        "abstract": "<p>abstract</p><p>two lines</p>",
        "headline": "test imatrics",
        "slugline": "test imatrics",
    }

    def setUp(self):
        self.app.config["IMATRICS_BASE_URL"] = TEST_BASE_URL
        self.app.config["IMATRICS_USER"] = "some_user"
        self.app.config["IMATRICS_KEY"] = "some_secret_key"
        self.app.config["IMATRICS_SUBJECT_SCHEME"] = "topics"
        registered_ai_services.clear()
        tools.import_services(self.app, ai.__name__, AIServiceBase)

    @responses.activate
    def test_autotagging(self):
        """Check that autotagging is working"""
        self.app.data.insert(
            "vocabularies",
            [
                {
                    "_id": "topics",
                    "items": [
                        {
                            "name": "superdesk name",
                            "qcode": "20000763",
                            "is_active": True,
                        },
                    ],
                }
            ],
        )

        doc = {
            "service": "imatrics",
            "item": self.item,
        }
        ai_service = get_resource_service("ai")
        api_url = urljoin(TEST_BASE_URL, "article/analysis")
        responses.add(
            responses.POST,
            api_url,
            match=[
                responses.json_params_matcher(
                    {
                        "uuid": self.item["guid"],
                        "pubStatus": False,
                        "headline": self.item["headline"],
                        "language": "en",
                        "body": [
                            "this is a fake article to test the imatrics service,"
                            " it should be returning some interesting tags.",
                            "abstract",
                            "two lines",
                        ],
                    }
                )
            ],
            json={
                "concepts": [
                    {
                        "weight": 1,
                        "geometry": {},
                        "links": [],
                        "title": "IT",
                        "type": "topic",
                        "uuid": "e3c482c0-08a4-3b31-a7f1-e231f1ddffc4",
                        "aliases": [],
                    },
                    {
                        "weight": 0.8387794287831216,
                        "geometry": {},
                        "links": [],
                        "title": "Service",
                        "type": "topic",
                        "uuid": "44f52663-52f9-3836-ac45-ae862fe945a3",
                        "aliases": [],
                    },
                    {
                        "weight": 1,
                        "geometry": {},
                        "links": [
                            {"relationType": "", "id": "medtop:20000763", "source": "IPTC", "uri": "", "url": ""}
                        ],
                        "title": "informasjons- og kommunikasjonsteknologi",
                        "type": "category",
                        "uuid": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                        "source": "source",
                        "aliases": ["foo"],
                        "shortDescription": "NaN",
                    },
                ]
            },
        )

        ai_service.create([doc])

        expected = {
            "subject": [
                {
                    "name": "IT",
                    "qcode": "e3c482c0-08a4-3b31-a7f1-e231f1ddffc4",
                    "scheme": "imatrics_topic",
                    "source": "imatrics",
                    "altids": {
                        "imatrics": "e3c482c0-08a4-3b31-a7f1-e231f1ddffc4",
                    },
                    "original_source": None,
                    "aliases": [],
                    "parent": None,
                },
                {
                    "name": "superdesk name",
                    "qcode": "20000763",
                    "scheme": "topics",
                    "source": "imatrics",
                    "altids": {
                        "imatrics": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                        "medtop": "20000763",
                    },
                    "original_source": "source",
                    "aliases": ["foo"],
                    "parent": None,
                },
                {
                    "name": "Service",
                    "qcode": "44f52663-52f9-3836-ac45-ae862fe945a3",
                    "scheme": "imatrics_topic",
                    "source": "imatrics",
                    "altids": {
                        "imatrics": "44f52663-52f9-3836-ac45-ae862fe945a3",
                    },
                    "original_source": None,
                    "aliases": [],
                    "parent": None,
                },
            ]
        }

        self.assertEqual(doc["analysis"], expected)

    @responses.activate
    def test_search(self):
        """Tag searching is returning tags"""
        doc = {
            "service": "imatrics",
            "operation": "search",
            "data": {"term": "informasjons"},
        }
        ai_data_op_service = get_resource_service("ai_data_op")
        api_url = urljoin(TEST_BASE_URL, "concept/get?operation=title_type")
        responses.add(
            responses.POST,
            api_url,
            json={
                "result": [
                    {
                        "longDescription": "",
                        "pubStatus": True,
                        "aliases": [],
                        "latestVersionTimestamp": "2020-07-14T15:26:26Z",
                        "author": "NTB",
                        "createdTimestamp": "2020-07-14T15:26:26Z",
                        "shortDescription": "title",
                        "broader": "",
                        "title": "informasjons- og kommunikasjonsteknologi",
                        "type": "category",
                        "uuid": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                    },
                    {
                        "longDescription": "",
                        "pubStatus": True,
                        "aliases": [],
                        "latestVersionTimestamp": "2020-07-14T15:26:24Z",
                        "author": "NTB",
                        "createdTimestamp": "2020-07-14T15:26:24Z",
                        "shortDescription": "title",
                        "broader": "",
                        "title": "informasjonsvitenskap",
                        "type": "category",
                        "uuid": "af815add-8456-3226-8177-ea0d8e3011eb",
                    },
                ],
                "response": "Request successful.",
                "error": False,
                "scrollID": "9e7da4cf-541f-36b1-b7a0-aa883a76c04f",
            },
        )
        ai_data_op_service.create([doc])

        expected = {
            "tags": {
                "subject": [
                    {
                        "name": "informasjons- og kommunikasjonsteknologi",
                        "qcode": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                        "scheme": "imatrics_category",
                        "source": "imatrics",
                        "description": "title",
                        "altids": {
                            "imatrics": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                        },
                        "aliases": [],
                        "original_source": None,
                        "parent": None,
                    },
                    {
                        "name": "informasjonsvitenskap",
                        "qcode": "af815add-8456-3226-8177-ea0d8e3011eb",
                        "scheme": "imatrics_category",
                        "source": "imatrics",
                        "description": "title",
                        "altids": {
                            "imatrics": "af815add-8456-3226-8177-ea0d8e3011eb",
                        },
                        "aliases": [],
                        "original_source": None,
                        "parent": None,
                    },
                ]
            }
        }

        self.assertEqual(doc["result"], expected)

    @responses.activate
    def test_create(self):
        """Tag can be created"""
        doc = {
            "service": "imatrics",
            "operation": "create",
            "data": {"title": "test_create"},
        }
        ai_data_op_service = get_resource_service("ai_data_op")
        api_url = urljoin(TEST_BASE_URL, "concept/create")
        responses.add(
            responses.POST,
            api_url,
            json={"response": "Concept created with uuid: 6083cb74-77b7-3046-8187-a6333b76b5a4.", "error": False},
        )
        ai_data_op_service.create([doc])
        self.assertEqual(doc["result"], {})

    @responses.activate
    def test_create_fail(self):
        """Tag creation conflict report raise an error"""
        doc = {
            "service": "imatrics",
            "operation": "create",
            "data": {"title": "test_create"},
        }
        ai_data_op_service = get_resource_service("ai_data_op")
        api_url = urljoin(TEST_BASE_URL, "concept/create")
        responses.add(
            responses.POST,
            api_url,
            json={
                "response": "A concept of type topic and title test_create already exists with uuid a2d0ce94-e4b2-3102-"
                "9671-9307b464573c.",
                "error": True,
            },
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
        ai_data_op_service = get_resource_service("ai_data_op")
        api_url = urljoin(TEST_BASE_URL, "concept/delete") + "?uuid=afc7e49d-57d0-34af-b184-b7600af362a9"
        responses.add(
            responses.DELETE,
            api_url,
            json={"error": False},
        )
        ai_data_op_service.create([doc])

        self.assertEqual(doc["result"], {})
