# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import datetime

import superdesk
from superdesk.tests import TestCase


class ArchiveGetItemsChainTestCase(TestCase):
    archive = [
        {
            "_id": "original",
            "guid": "original",
            "headline": "Original EN",
            "translations": ["original-translation-fr", "original-translation-nl"],
            "rewritten_by": "update-1",
            "language": "en",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "original-translation-fr",
            "guid": "original-translation-fr",
            "headline": "Original Translation FR",
            "translated_from": "original",
            "language": "fr",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "original-translation-nl",
            "guid": "original-translation-nl",
            "headline": "Original Translation NL",
            "translated_from": "original",
            "language": "nl",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "update-1",
            "guid": "update-1",
            "headline": "Update 1 EN",
            "translations": [],
            "rewritten_by": "update-2",
            "rewrite_of": "original",
            "language": "en",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "update-2",
            "guid": "update-2",
            "headline": "Update 2 EN",
            "translations": [
                "update-2-translation-fr",
            ],
            "rewrite_of": "update-1",
            "language": "en",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "update-2-translation-fr",
            "guid": "update-2-translation-fr",
            "headline": "Update 2 Translation FR",
            "translated_from": "update-2",
            "translations": [
                "update-2-translation-fr-nl",
            ],
            "language": "fr",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "update-2-translation-fr-nl",
            "guid": "update-2-translation-fr-nl",
            "headline": "Update 2 Translation FR NL",
            "translated_from": "update-2-translation-fr",
            "language": "nl",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "update-2-translation-fr-nl-update",
            "guid": "update-2-translation-fr-nl-update",
            "headline": "Update 2 Translation FR NL update",
            "rewrite_of": "update-2-translation-fr-nl",
            "language": "nl",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
        {
            "_id": "update-2-translation-fr-nl-update-2",
            "guid": "update-2-translation-fr-nl-update-2",
            "headline": "Update 2 Translation FR NL update",
            "rewrite_of": "update-2-translation-fr-nl-update",
            "language": "nl",
            "type": "text",
            "version": 1,
            "profile": "text",
            "pubstatus": "usable",
            "format": "HTML",
            "firstcreated": datetime.datetime(2019, 4, 3, 12, 41, 53),
            "versioncreated": datetime.datetime(2019, 4, 3, 12, 45, 14),
            "original_creator": "5d385f31fe985ec67a0ca583",
            "state": "published",
            "source": "Belga",
            "version_creator": "5d385f31fe985ec67a0ca583",
            "slugline": "skoda scala",
            "byline": "BELGA",
        },
    ]

    def setUp(self):
        self.app.data.insert("archive", self.archive)

    def test_get_items_chain(self):
        archive_service = superdesk.get_resource_service("archive")

        original = self.archive[0]
        items = archive_service.get_items_chain(original)
        self.assertListEqual(
            [i["_id"] for i in items], ["original", "original-translation-fr", "original-translation-nl"]
        )

        original_translation_fr = self.archive[1]
        items = archive_service.get_items_chain(original_translation_fr)
        self.assertListEqual(
            [i["_id"] for i in items], ["original", "original-translation-fr", "original-translation-nl"]
        )

        original_translation_nl = self.archive[2]
        items = archive_service.get_items_chain(original_translation_nl)
        self.assertListEqual(
            [i["_id"] for i in items], ["original", "original-translation-fr", "original-translation-nl"]
        )

        update_1 = self.archive[3]
        items = archive_service.get_items_chain(update_1)
        self.assertListEqual(
            [i["_id"] for i in items], ["original", "original-translation-fr", "original-translation-nl", "update-1"]
        )

        update_2 = self.archive[4]
        items = archive_service.get_items_chain(update_2)
        self.assertListEqual(
            [i["_id"] for i in items],
            [
                "original",
                "original-translation-fr",
                "original-translation-nl",
                "update-1",
                "update-2",
                "update-2-translation-fr",
                "update-2-translation-fr-nl",
            ],
        )

        update_2_translation_fr = self.archive[5]
        items = archive_service.get_items_chain(update_2_translation_fr)
        self.assertListEqual(
            [i["_id"] for i in items],
            [
                "original",
                "original-translation-fr",
                "original-translation-nl",
                "update-1",
                "update-2",
                "update-2-translation-fr",
                "update-2-translation-fr-nl",
            ],
        )

        update_2_translation_fr_nl = self.archive[6]
        items = archive_service.get_items_chain(update_2_translation_fr_nl)
        self.assertListEqual(
            [i["_id"] for i in items],
            [
                "original",
                "original-translation-fr",
                "original-translation-nl",
                "update-1",
                "update-2",
                "update-2-translation-fr",
                "update-2-translation-fr-nl",
            ],
        )

        update_2_translation_fr_nl_update = self.archive[7]
        items = archive_service.get_items_chain(update_2_translation_fr_nl_update)
        self.assertListEqual(
            [i["_id"] for i in items],
            [
                "original",
                "original-translation-fr",
                "original-translation-nl",
                "update-1",
                "update-2",
                "update-2-translation-fr",
                "update-2-translation-fr-nl",
                "update-2-translation-fr-nl-update",
            ],
        )

        update_2_translation_fr_nl_update_2 = self.archive[8]
        items = archive_service.get_items_chain(update_2_translation_fr_nl_update_2)
        self.assertListEqual(
            [i["_id"] for i in items],
            [
                "original",
                "original-translation-fr",
                "original-translation-nl",
                "update-1",
                "update-2",
                "update-2-translation-fr",
                "update-2-translation-fr-nl",
                "update-2-translation-fr-nl-update",
                "update-2-translation-fr-nl-update-2",
            ],
        )
