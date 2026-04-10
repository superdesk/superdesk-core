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
from superdesk.tests import TestCase
from superdesk.io.feed_parsers.ap_media import APMediaFeedParser
import json


class APMediaTestCase(TestCase):
    vocab = [{"_id": "genre", "items": [{"name": "Current"}]}]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.data.insert("vocabularies", self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        with open(fixture) as fp:
            self.item = await APMediaFeedParser().parse(json.load(fp), provider)


class SimpleTestCase(APMediaTestCase):
    filename = "ap_media_picture.json"

    def test_headline(self):
        self.assertEqual(self.item.get("headline"), "US Paul Simon Poets Society")


class AssociationsErrorHandlingTest(TestCase):
    async def test_parse_associations_ignores_invalid_association_items(self):
        parser = APMediaFeedParser()
        parser.RELATED_ID = "related"

        parsed = await parser.parse(
            {
                "data": {
                    "item": {
                        "altids": {"itemid": "main"},
                        "version": 1,
                        "type": "text",
                        "slugline": "MAIN-SLUG",
                    }
                },
                "api_version": "1.0",
                "associations": {
                    "good": {
                        "data": {
                            "item": {
                                "altids": {"itemid": "assoc"},
                                "version": 1,
                                "type": "text",
                                "slugline": "ASSOC-SLUG",
                            }
                        },
                        "api_version": "1.0",
                    },
                    "bad": {"data": {}},
                },
            },
            {"source": "Test"},
        )

        self.assertIn("associations", parsed)
        self.assertIn("related--good", parsed["associations"])
        self.assertNotIn("related--bad", parsed["associations"])
