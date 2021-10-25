# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import bson
from superdesk.tests import TestCase
from superdesk import get_resource_service
from superdesk.commands.update_archived_document import UpdateArchivedDocumentCommand


class UpdateArchivedDocumentTestCase(TestCase):
    def setUp(self):
        self.guid = "urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a"

        self.archived_only_data = [
            {
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
                "source": "AAP",
                "linked_in_packages": [
                    {
                        "package": "urn:newsml:localhost:2017-01-28T15:28:33.535974:30c01757-cfb5-4985-a8f4-c3ecb253a244",
                        "package_type": "takes",
                    }
                ],
            },
            {
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
                "source": "AAP",
            },
        ]

        self.archivedService = get_resource_service("archived")

    def test_update_source(self):
        self.archivedService.post(self.archived_only_data)
        UpdateArchivedDocumentCommand().run("['588c1b901d41c805dce70df0']", "source", "NTB")

        item = self.archivedService.get(req=None, lookup={"_id": "588c1b901d41c805dce70df0"})
        self.assertEqual("NTB", item[0].get("source"))

    def test_update_anpa_category_for_multiple_document(self):
        self.archivedService.post(self.archived_only_data)
        UpdateArchivedDocumentCommand().run(
            "['588c1b901d41c805dce70df0', '57d224de069b7f038e9d2a53']",
            "anpa_category",
            '[{"scheme":null,"qcode":"f","subject":"04000000","name":"Finance"}]',
            True,
        )

        item = self.archivedService.get(req=None, lookup={"_id": "588c1b901d41c805dce70df0"})
        self.assertEqual("f", item[0].get("anpa_category")[0].get("qcode"))
        item = self.archivedService.get(req=None, lookup={"_id": "57d224de069b7f038e9d2a53"})
        self.assertEqual("f", item[0].get("anpa_category")[0].get("qcode"))
