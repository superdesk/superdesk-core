# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import json
from unittest.mock import patch

from apps.prepopulate.app_populate import AppPopulateCommand
from superdesk.tests import TestCase
from superdesk import get_resource_service
from superdesk.vocabularies import VocabulariesService
from superdesk.errors import SuperdeskApiError


class VocabulariesPopulateTest(TestCase):
    def setUp(self):
        self.filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), "vocabularies.json")
        self.json_data = [
            {
                "_id": "categories",
                "unique_field": "qcode",
                "items": [
                    {"name": "National", "qcode": "A", "is_active": True},
                    {"name": "Domestic Sports", "qcode": "T", "is_active": False},
                ],
            },
            {
                "_id": "newsvalue",
                "items": [
                    {"name": "1", "value": "1", "is_active": True},
                    {"name": "2", "value": "2", "is_active": True},
                    {"name": "3", "value": "3", "is_active": False},
                ],
            },
        ]

        with open(self.filename, "w+") as file:
            json.dump(self.json_data, file)

    def test_populate_vocabularies(self):
        cmd = AppPopulateCommand()
        cmd.run(self.filename)
        service = get_resource_service("vocabularies")

        for item in self.json_data:
            data = service.find_one(_id=item["_id"], req=None)
            self.assertEqual(data["_id"], item["_id"])
            self.assertListEqual(data["items"], item["items"])

    def test_check_uniqueness(self):
        items = [
            {"name": "National", "qcode": "A", "is_active": True},
            {"name": "Domestic Sports", "qcode": "a", "is_active": True},
        ]
        with self.assertRaises(SuperdeskApiError):
            VocabulariesService()._check_uniqueness(items, "qcode")

    def test_check_uniqueness_active_only(self):
        items = [
            {"name": "National", "qcode": "A", "is_active": True},
            {"name": "Domestic Sports", "qcode": "A", "is_active": False},
        ]
        VocabulariesService()._check_uniqueness(items, "qcode")

    def test_check_value_of_unique_field(self):
        items = [{"name": "National", "is_active": True}, {"name": "Domestic Sports", "qcode": "A", "is_active": True}]
        with self.assertRaises(SuperdeskApiError):
            VocabulariesService()._check_uniqueness(items, "qcode")

    def test_get_rightsinfo(self):
        service = get_resource_service("vocabularies")
        vocab = {
            "_id": "rightsinfo",
            "items": [
                {
                    "is_active": True,
                    "name": "default",
                    "copyrightHolder": "default holder",
                    "copyrightNotice": "default notice",
                    "usageTerms": "default terms",
                },
                {
                    "is_active": True,
                    "name": "foo",
                    "copyrightHolder": "foo holder",
                    "copyrightNotice": "foo notice",
                    "usageTerms": "foo terms",
                },
            ],
        }

        with patch.object(service, "find_one", return_value=vocab):
            info = service.get_rightsinfo({})
            self.assertEqual("default holder", info["copyrightholder"])
            self.assertEqual("default notice", info["copyrightnotice"])
            self.assertEqual("default terms", info["usageterms"])
            info = service.get_rightsinfo({"source": "foo"})
            self.assertEqual("foo holder", info["copyrightholder"])
            self.assertEqual("foo notice", info["copyrightnotice"])
            self.assertEqual("foo terms", info["usageterms"])

    def test_get_locale_vocabulary(self):
        items = [
            {
                "is_active": True,
                "name": "FIXME1",
                "qcode": "f",
                "subject": "",
                "translations": {"name": {"fr": "FIXME1-fr", "es": "FIXME1-es"}},
            },
            {
                "is_active": True,
                "name": "FIXME2",
                "qcode": "f",
                "subject": "",
                "translations": {"name": {"fr": "FIXME2-fr", "es": "FIXME2-es"}},
            },
        ]
        result = VocabulariesService().get_locale_vocabulary(items, "fr")

        self.assertEqual(result[0]["name"], "FIXME1-fr")
        self.assertEqual(result[1]["name"], "FIXME2-fr")

    def tearDown(self):
        os.remove(self.filename)
