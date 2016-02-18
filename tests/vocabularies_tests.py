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
from superdesk.tests import TestCase
from superdesk import get_resource_service
from superdesk.vocabularies import VocabulariesService
from superdesk.vocabularies.command import VocabulariesPopulateCommand
from superdesk.errors import SuperdeskApiError


class VocabulariesPopulateTest(TestCase):

    def setUp(self):
        super().setUp()
        self.filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), "vocabularies.json")
        self.json_data = [
            {"_id": "categories",
             "unique_field": "qcode",
             "items": [
                 {"name": "National", "qcode": "A", "is_active": True},
                 {"name": "Domestic Sports", "qcode": "T", "is_active": False}
             ]},
            {"_id": "newsvalue",
             "items": [
                 {"name": "1", "value": "1", "is_active": True},
                 {"name": "2", "value": "2", "is_active": True},
                 {"name": "3", "value": "3", "is_active": False}
             ]}
        ]

        with open(self.filename, "w+") as file:
            json.dump(self.json_data, file)

    def test_populate_vocabularies(self):
        cmd = VocabulariesPopulateCommand()
        cmd.run(self.filename)
        service = get_resource_service("vocabularies")

        for item in self.json_data:
            data = service.find_one(_id=item["_id"], req=None)
            self.assertEqual(data["_id"], item["_id"])
            self.assertListEqual(data["items"], item["items"])

    def test_check_uniqueness(self):
        items = [{"name": "National", "qcode": "A", "is_active": True},
                 {"name": "Domestic Sports", "qcode": "a", "is_active": True}]
        with self.assertRaises(SuperdeskApiError):
            VocabulariesService()._check_uniqueness(items, "qcode")

    def test_check_uniqueness_active_only(self):
        items = [{"name": "National", "qcode": "A", "is_active": True},
                 {"name": "Domestic Sports", "qcode": "A", "is_active": False}]
        VocabulariesService()._check_uniqueness(items, "qcode")

    def test_check_value_of_unique_field(self):
        items = [{"name": "National", "is_active": True},
                 {"name": "Domestic Sports", "qcode": "A", "is_active": True}]
        with self.assertRaises(SuperdeskApiError):
            VocabulariesService()._check_uniqueness(items, "qcode")

    def tearDown(self):
        os.remove(self.filename)
        super().tearDown()
