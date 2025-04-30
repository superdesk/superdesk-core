# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId

from superdesk.core import json
from superdesk.publish import init_app
from superdesk.publish.transmitters.odbc import ODBCPublishService
from superdesk.tests import TestCase, utils as test_utils, fixtures


class ODBCTests(TestCase):
    products = fixtures.products.all_products()
    subscribers = fixtures.subscribers.all_subscribers()

    queue_items = [
        {
            "_id": ObjectId(),
            "state": "pending",
            "content_type": "text",
            "headline": "test",
            "unique_name": "#2034",
            "publishing_action": "published",
            "published_seq_num": 4,
            "destination": {
                "name": "AAP IPNEWS",
                "delivery_type": "odbc",
                "format": "AAP IPNEWS",
                "config": {"stored_procedure": "InsertNews"},
            },
            "formatted_item": json.dumps(
                {
                    "ident": "0",
                    "selector_codes": "3**",
                    "wordcount": 313,
                    "texttab": "x",
                    "originator": "AAP",
                    "service_level": "a",
                    "keyword": "ROSS",
                    "subject": "crime, law and justice",
                    "category": "a",
                    "take_key": "Take-that",
                    "subject_detail": "international court or tribunal",
                    "subject_reference": "02011001",
                    "article_text": "THIS IS A TEST PLEASE IGNORE",
                    "priority": "u",
                    "headline": "TEST HEADLINE",
                    "usn": 68147,
                    "subject_matter": "international law",
                    "sequence": 117,
                    "news_item_type": "News",
                    "author": "",
                    "genre": "Current",
                    "fullStory": 1,
                }
            ),
            "subscriber_id": fixtures.subscribers.SUB1_ID,
            "item_id": "1",
            "item_version": 6,
        }
    ]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await test_utils.post_items("products", self.products)
        self.subscribers[0].destinations[0].config["connection_string"] = self.app.config["ODBC_TEST_CONNECTION_STRING"]
        await test_utils.post_items("subscribers", self.subscribers)

        self.queue_items[0]["destination"]["config"]["connection_string"] = self.app.config[
            "ODBC_TEST_CONNECTION_STRING"
        ]
        await test_utils.post_items("publish_queue", self.queue_items)
        init_app(self.app)

    async def test_transmit(self):
        if self.app.config["ODBC_PUBLISH"]:
            subscriber = list(await test_utils.find_many("subscribers"))[0]

            publish_service = ODBCPublishService()
            ret = publish_service._transmit(self.queue_items[0], subscriber)
            self.assertGreater(ret, 0)
