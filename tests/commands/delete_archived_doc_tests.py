# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import io
import bson
from contextlib import redirect_stdout
from superdesk.tests import TestCase
from superdesk import get_resource_service
from superdesk.commands.delete_archived_document import DeleteArchivedDocumentCommand


class DeleteDocTestCase(TestCase):

    def setUp(self):
        self.guid = 'urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a'

        self.archived_only_data = [{
            "_id": bson.ObjectId("588c1b901d41c805dce70df0"),
            "guid": self.guid,
            "item_id": self.guid,
            "_current_version": 3,
            "type": "text",
            "abstract": "test",
            "state": "fetched",
            "slugline": "slugline",
            "headline": "headline",
            "flags": {"marked_archived_only": True},
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Test Document body",
            'source': 'AAP',
            'linked_in_packages': [{
                "package": "urn:newsml:localhost:2017-01-28T15:28:33.535974:30c01757-cfb5-4985-a8f4-c3ecb253a244",
                "package_type": "takes"}]

        }, {
            "_id": bson.ObjectId("57d224de069b7f038e9d2a53"),
            "guid": "urn:newsml:localhost:2016-08-30T06:15:35.379754:3d68cc4c-1f16-4a7f-bfca-92ca50bcdd8f",
            "item_id": "urn:newsml:localhost:2016-08-30T06:15:35.379754:3d68cc4c-1f16-4a7f-bfca-92ca50bcdd8f",
            "_current_version": 4,
            "type": "text",
            "abstract": "test",
            "state": "fetched",
            "slugline": "slugline",
            "headline": "headline",
            "flags": {"marked_archived_only": True},
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Test Document body",
            'source': 'AAP'
        }, {
            "_id": "213456",
            "guid": self.guid,
            "item_id": "urn:newsml:localhost:2017-01-28T15:28:33.535974:30c01757-cfb5-4985-a8f4-c3ecb253a244",
            "_current_version": 1,
            "type": "composite",
            "abstract": "test",
            "state": "fetched",
            "slugline": "slugline",
            "headline": "headline",
            "groups": [
                {
                    "id": "root",
                    "refs": [
                        {
                            "idRef": "main"
                        }
                    ],
                    "role": "grpRole:NEP"
                },
                {
                    "id": "main",
                    "refs": [
                        {
                            "residRef":
                                "urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a",
                            "guid":
                                "urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a",
                            "itemClass": "icls:text",
                            "headline": "Testing takes",
                            "type": "text",
                            "renditions": {

                            },
                            "_current_version": 3,
                            "is_published": True,
                            "slugline": "Takes test",
                            "sequence": 1,
                            "location": "archived"
                        },
                        {
                            "residRef":
                                "urn:newsml:localhost:2016-08-30T06:15:35.379754:3d68cc4c-1f16-4a7f-bfca-92ca50bcdd8f",
                            "guid":
                                "urn:newsml:localhost:2016-08-30T06:15:35.379754:3d68cc4c-1f16-4a7f-bfca-92ca50bcdd8f",
                            "itemClass": "icls:text",
                            "headline": "Testing takes",
                            "type": "text",
                            "renditions": {

                            },
                            "_current_version": 4,
                            "is_published": True,
                            "slugline": "Takes test",
                            "sequence": 2,
                            "location": "archived"
                        }
                    ],
                    "role": "grpRole:main"
                }
            ]
        }
        ]

        self.archivedService = get_resource_service('archived')

    def test_no_id_provided_exception(self):
        self.archivedService.post(self.archived_only_data)

        f = io.StringIO()
        with redirect_stdout(f):
            DeleteArchivedDocumentCommand().run([])
        s = f.getvalue()
        self.assertEqual(s, 'Please provide at least one id!\n')

    def test_wrong_id_provided_exception(self):
        self.archivedService.post(self.archived_only_data)

        f = io.StringIO()
        with redirect_stdout(f):
            DeleteArchivedDocumentCommand().run(['5880000000000'])
        s = f.getvalue()
        self.assertIn('No archived story found with given ids(s)!\n', s)

    def test_delete_non_text_document_succeeds(self):
        self.archivedService.post(self.archived_only_data)

        DeleteArchivedDocumentCommand().run(['213456'])
        cursor = self.archivedService.get(req=None, lookup={'_id': '213456'})
        self.assertEqual(0, len(cursor.docs))

    def test_delete_document_succeeds(self):
        self.archivedService.post(self.archived_only_data)
        DeleteArchivedDocumentCommand().run(['588c1b901d41c805dce70df0'])

        cursor = self.archivedService.get(req=None, lookup={'_id': '588c1b901d41c805dce70df0'})
        self.assertEqual(0, len(cursor.docs))
        cursor = self.archivedService.get(req=None, lookup={'_id': '213456'})
        self.assertEqual(0, len(cursor.docs))

    def test_delete_multiple_documents_succeeds(self):
        self.archivedService.post(self.archived_only_data)
        DeleteArchivedDocumentCommand().run(['588c1b901d41c805dce70df0', '57d224de069b7f038e9d2a53'])

        cursor = self.archivedService.get(req=None, lookup={'_id': '588c1b901d41c805dce70df0'})
        self.assertEqual(0, len(cursor.docs))
        cursor = self.archivedService.get(req=None, lookup={'_id': '57d224de069b7f038e9d2a53'})
        self.assertEqual(0, len(cursor.docs))

    def test_deleting_one_take_deletes_package_but_keeps_other_takes_succeeds(self):
        # it will delete other takes in that package
        self.archivedService.post(self.archived_only_data)
        DeleteArchivedDocumentCommand().run(['588c1b901d41c805dce70df0'])

        cursor = self.archivedService.get(req=None, lookup={'_id': '588c1b901d41c805dce70df0'})
        self.assertEqual(0, len(cursor.docs))
        cursor = self.archivedService.get(req=None, lookup={'_id': '213456'})
        self.assertEqual(0, len(cursor.docs))
        cursor = self.archivedService.get(req=None, lookup={'_id': '57d224de069b7f038e9d2a53'})
        self.assertEqual(1, len(cursor.docs))
