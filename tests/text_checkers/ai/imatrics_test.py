# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import responses
from urllib.parse import urljoin
from superdesk.tests import TestCase
from superdesk.text_checkers import tools
from superdesk.text_checkers import ai
from superdesk.text_checkers.ai.base import registered_ai_services, AIServiceBase
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service

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
                },
                {
                    "_id": "place_custom",
                    "items": [
                        {
                            "name": "test-place",
                            "qcode": "123",
                            "is_active": True,
                        },
                    ],
                },
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
                        "type": "place",
                        "uuid": "123",
                        "title": "imatrics place",
                        "wikidata": "Q123",
                    },
                ],
                "broader": [
                    {
                        "weight": 1,
                        "geometry": {},
                        "links": [
                            {
                                "relationType": "exactMatch",
                                "id": "medtop:20000763",
                                "source": "iptc",
                                "uri": "",
                                "url": "",
                            }
                        ],
                        "title": "informasjons- og kommunikasjonsteknologi",
                        "type": "category",
                        "uuid": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                        "source": "source",
                        "aliases": ["foo"],
                        "shortDescription": "NaN",
                    },
                ],
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
            ],
            "place": [
                {
                    "name": "test-place",
                    "qcode": "123",
                    "scheme": "place_custom",
                    "original_source": None,
                    "aliases": [],
                    "altids": {
                        "imatrics": "123",
                    },
                    "parent": None,
                    "source": "imatrics",
                },
            ],
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
        api_url = urljoin(TEST_BASE_URL, "concept/get")
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
                        "scheme": "mediatopic",
                        "source": "imatrics",
                        "description": "title",
                        "altids": {
                            "imatrics": "c8a83204-29e0-3a7f-9a0e-51e76d885f7f",
                        },
                        "aliases": [],
                        "original_source": "NTB",
                        "parent": None,
                    },
                    {
                        "name": "informasjonsvitenskap",
                        "qcode": "af815add-8456-3226-8177-ea0d8e3011eb",
                        "scheme": "mediatopic",
                        "source": "imatrics",
                        "description": "title",
                        "altids": {
                            "imatrics": "af815add-8456-3226-8177-ea0d8e3011eb",
                        },
                        "aliases": [],
                        "original_source": "NTB",
                        "parent": None,
                    },
                ]
            },
            "broader": {
                "subject": [],
            },
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

    @responses.activate
    def test_feedback(self):
        """Send feedback to the service on save."""
        doc = {
            "service": "imatrics",
            "operation": "feedback",
            "data": {
                "item": {
                    "guid": "afc7e49d-57d0-34af-b184-b7600af362a9",
                    "language": "en",
                    "headline": "test",
                    "body_html": "<p>body</p>",
                },
                "tags": {
                    "subject": [
                        {
                            "name": "medier",
                            "description": "The various means of disseminating news and information to the public",
                            "qcode": "20000304",
                            "source": "imatrics",
                            "altids": {
                                "imatrics": "7ac790f9-e6d1-3972-a28c-e7ddbe6161df",
                                "medtop": "20000304",
                                "wikidata": "Q56611639",
                            },
                            "parent": "20000209",
                            "scheme": "topics",
                            "aliases": [],
                            "original_source": None,
                        },
                        {
                            "name": "massemedier",
                            "description": "Media addressing a large audience",
                            "qcode": "20000045",
                            "source": "imatrics",
                            "altids": {
                                "imatrics": "20727888-04fa-3d53-9a8b-47ccd89a1a6d",
                                "medtop": "20000045",
                                "wikidata": "Q11033",
                            },
                            "parent": "01000000",
                            "scheme": "topics",
                            "aliases": [],
                            "original_source": None,
                        },
                    ],
                    "organisation": [
                        {
                            "name": "CNN",
                            "description": "internasjonal nyhets-tv-kanal",
                            "qcode": "88dc48b5-72ed-35cb-9a6a-56981e12b414",
                            "source": "imatrics",
                            "altids": {"imatrics": "88dc48b5-72ed-35cb-9a6a-56981e12b414", "wikidata": "Q48340"},
                            "aliases": ["Cable News Network"],
                            "original_source": "wikidata",
                        }
                    ],
                    "place": [
                        {
                            "name": "Hongkong",
                            "description": "administrativ region i Kina",
                            "qcode": "3b7a17e2-18f5-36d0-8d87-a5daf9595fef",
                            "source": "imatrics",
                            "altids": {"imatrics": "3b7a17e2-18f5-36d0-8d87-a5daf9595fef", "wikidata": "Q8646"},
                            "aliases": ["Hong Kong"],
                            "original_source": "1013",
                            "scheme": "place_custom",
                        }
                    ],
                },
            },
        }

        responses.add(
            responses.POST,
            url=self.app.config["IMATRICS_BASE_URL"] + "/article/concept",
            json={"uuid": "guid"},
        )

        ai_data_op_service = get_resource_service("ai_data_op")
        ai_data_op_service.create([doc])

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            {
                "uuid": "afc7e49d-57d0-34af-b184-b7600af362a9",
                "language": "en",
                "headline": "test",
                "body": ["body"],
                "pubStatus": True,
                "concepts": [
                    {
                        "title": "medier",
                        "type": "category",
                        "uuid": "7ac790f9-e6d1-3972-a28c-e7ddbe6161df",
                    },
                    {
                        "title": "massemedier",
                        "type": "category",
                        "uuid": "20727888-04fa-3d53-9a8b-47ccd89a1a6d",
                    },
                    {
                        "title": "CNN",
                        "type": "organisation",
                        "uuid": "88dc48b5-72ed-35cb-9a6a-56981e12b414",
                    },
                    {
                        "title": "Hongkong",
                        "type": "place",
                        "uuid": "3b7a17e2-18f5-36d0-8d87-a5daf9595fef",
                    },
                ],
            },
            json.loads(responses.calls[0].request.body.decode()),
        )
