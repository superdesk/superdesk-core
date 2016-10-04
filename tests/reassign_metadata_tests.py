# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.tests import TestCase
from superdesk import get_resource_service
from superdesk.commands.reassign_metadata import ReassignMetadataCommand


class ReassignMetadataTestCase(TestCase):

    def setUp(self):
        self.guid = 'urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a'

        self.archived_only_data = [{
            "_id": "test1",
            "guid": self.guid,
            "item_id": "urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a",
            "_current_version": "1",
            "type": "text",
            "abstract": "test",
            "state": "fetched",
            "slugline": "slugline",
            "headline": "headline",
            "flags": {"marked_archived_only": True},
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Test Document body",
            'source': 'AAP',
            'anpa_category': [{
                'qcode': 'test',
                'name': 'Fake',
                'subject': None,
                'scheme': None
            }]
        }]

        vocab = [{
            "_id": "categories",
            "display_name": "Categories",
            "type": "manageable",
            "unique_field": "qcode",
            "items": [
                {"is_active": True, "name": "State Parliaments", "qcode": "o", "subject": "11000000"},
                {"is_active": True, "name": "Domestic Sport", "qcode": "t", "subject": "15000000"},
                {"is_active": True, "name": "Sport", "qcode": "s"},
                {"is_active": False, "name": "Reserved (Obsolete/unused)", "qcode": "u"},
            ]
        }]

        get_resource_service('vocabularies').post(vocab)
        self.archivedService = get_resource_service('archived')

    def test_check_valid_metadata(self):
        with self.assertRaises(SystemExit):
            ReassignMetadataCommand().run([self.guid], 'fake', 'fake')

    def test_check_valid_category(self):
        with self.assertRaises(SystemExit):
            ReassignMetadataCommand().run([self.guid], 'anpa_category', 'fake')

    def test_reassign_source(self):
        self.archivedService.post(self.archived_only_data)
        ReassignMetadataCommand().run([self.guid], 'source', 'NTB')

        cursor = self.archivedService.get(req=None, lookup={'guid': self.guid})
        self.assertEqual('NTB', cursor[0].get('source'))

    def test_reassign_source_multiple_versions(self):
        self.archivedService.post(self.archived_only_data)
        version_two = [{
            "_id": "test2",
            "guid": self.guid,
            "item_id": "urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a",
            "_current_version": "2",
            "type": "text",
            "abstract": "test 2",
            "state": "fetched",
            "slugline": "slugline",
            "headline": "headline",
            "flags": {"marked_archived_only": True},
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Test Document body 2",
            'source': 'AAP',
            'anpa_category': [{
                'qcode': 'test',
                'name': 'Fake',
                'subject': None,
                'scheme': None
            }]
        }]
        self.archivedService.post(version_two)
        ReassignMetadataCommand().run([self.guid], 'source', 'NTB')

        cursor = self.archivedService.get(req=None, lookup={'guid': self.guid})
        self.assertEqual(2, len(cursor.docs))
        self.assertEqual('NTB', cursor[0].get('source'))
        self.assertEqual('NTB', cursor[1].get('source'))

    def test_reassign_category_without_subject(self):
        self.archivedService.post(self.archived_only_data)
        ReassignMetadataCommand().run([self.guid], 'anpa_category', 's')

        cursor = self.archivedService.get(req=None, lookup={'guid': self.guid})

        updates = [{
            'qcode': 's',
            'name': 'Sport',
            'subject': None,
            'scheme': None
        }]
        self.assertEqual(updates, cursor[0].get('anpa_category'))

    def test_reassign_category_with_subject(self):
        self.archivedService.post(self.archived_only_data)
        ReassignMetadataCommand().run([self.guid], 'anpa_category', 'o')

        cursor = self.archivedService.get(req=None, lookup={'guid': self.guid})

        updates = [{
            'qcode': 'o',
            'name': 'State Parliaments',
            'subject': '11000000',
            'scheme': None
        }]
        self.assertEqual(updates, cursor[0].get('anpa_category'))
