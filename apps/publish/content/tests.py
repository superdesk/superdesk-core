# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

# TODO-ASYNC-PR: Update this file to use the new publish system

import os
import json
import tempfile
from copy import copy
from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock

from bson.objectid import ObjectId
from eve.utils import ParsedRequest
from eve.versioning import versioned_id_field

from superdesk.types import (
    SubscribersResource,
    ProductsResource,
    ProductFilterType,
    ProductContentFilter,
    PublishRequest,
    SubscriberType,
)
from superdesk.resource_fields import ID_FIELD, VERSION
from superdesk.errors import SuperdeskApiError
from apps.archive.archive import SOURCE as ARCHIVE
from apps.packages.package_service import PackageService
from apps.publish.content.common import BasePublishService
from apps.publish.content.publish import ArchivePublishService
from apps.publish.published_item import LAST_PUBLISHED_VERSION
from apps.prepopulate.app_populate import AppPopulateCommand
from superdesk import get_resource_service, get_backend
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE
from superdesk.publish import init_app
from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.tests import TestCase, utils as test_utils
from superdesk.utc import utcnow
from apps.archive.common import ITEM_OPERATION
from celery.exceptions import SoftTimeLimitExceeded
from superdesk.publish_async import get_exchange_factory
from superdesk.publish_async.utils import (
    item_target_matches_product_target,
    item_matches_product_filters,
    item_target_matches_subscriber_target,
)
from superdesk.publish_async.publish_cache import PublishCache
from superdesk.publish_async.filters import BasePublishExchangeFilter
from superdesk.tests import fixtures, markers
from superdesk.default_settings import PUBLISH_MODULES


async def enqueue_published():
    await get_exchange_factory().send_scheduled_or_pending_content()


def get_enqueue_service():
    pass


ARCHIVE_PUBLISH = "archive_publish"
ARCHIVE_CORRECT = "archive_correct"
ARCHIVE_KILL = "archive_kill"

PUBLISH_QUEUE = "publish_queue"
PUBLISHED = "published"

FILTER_CONDITION_IDS = [ObjectId(), ObjectId(), ObjectId(), ObjectId()]
CONTENT_FILTER_ID = ObjectId()


# TODO-ASYNC-PR: Update these tests to use async
#                   * Fix IDs used in this file, to use ObjectId where appropriate, fix other validation issues
# @mock.patch("superdesk.publish.subscribers.SubscribersService.generate_sequence_number", lambda self, subscriber: 1)
class ArchivePublishTestCase(TestCase):
    filter: BasePublishExchangeFilter
    app_config = {
        "PUBLISH_MODULES": PUBLISH_MODULES + ["superdesk.tests.publish.mock_consumer"],
        "PUBLISH_EXCHANGE_FACTORY": "superdesk.tests.publish.exchange_factory:MockPublishExchangeFactory",
    }

    def init_data(self):
        self.users = fixtures.users.all_users()
        self.desks = fixtures.desks.all_desks()
        self.products = fixtures.products.all_products()
        self.subscribers = fixtures.subscribers.all_subscribers()
        self.articles = fixtures.articles.all_articles()

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.init_data()

        await test_utils.post_items("users", self.users)
        await test_utils.post_items("desks", self.desks)
        await test_utils.post_items("products", self.products)
        await test_utils.post_items("subscribers", self.subscribers)
        await test_utils.post_items(ARCHIVE, self.articles, use_eve=True)

        self.article_versions = self._init_article_versions()

        with tempfile.TemporaryDirectory() as tmp:
            json_data = [
                {"_id": "kill_text", "act": "kill", "type": "text", "schema": {"headline": {"type": "string"}}},
                {"_id": "publish_text", "act": "publish", "type": "text", "schema": {}},
                {"_id": "correct_text", "act": "correct", "type": "text", "schema": {}},
                {"_id": "publish_composite", "act": "publish", "type": "composite", "schema": {}},
            ]

            filename = os.path.join(tmp, "validators.json")
            with open(filename, "w") as file:
                json.dump(json_data, file)

            init_app(self.app)
            await AppPopulateCommand().run(filename)

        self.app.media.url_for_media = MagicMock(return_value="url_for_media")
        self._put = self.app.media.put
        self.app.media.put = MagicMock(return_value="media_id")

        await PublishCache.init(force=True)
        self.filter = BasePublishExchangeFilter()

    async def asyncTearDown(self):
        self.app.media.put = self._put
        await super().asyncTearDown()

    def _init_article_versions(self):
        resource_def = self.app.config["DOMAIN"]["archive_versions"]
        version_id = versioned_id_field(resource_def)
        return [
            {
                "guid": "tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9",
                version_id: "1",
                ITEM_TYPE: CONTENT_TYPE.TEXT,
                VERSION: 1,
                "urgency": 4,
                "pubstatus": "usable",
                "firstcreated": utcnow(),
                "byline": "By Alan Karben",
                "dateline": {"located": {"city": "Sydney"}},
                "keywords": ["Student", "Crime", "Police", "Missing"],
                "subject": [{"qcode": "17004000", "name": "Statistics"}, {"qcode": "04001002", "name": "Weather"}],
                ITEM_STATE: CONTENT_STATE.DRAFT,
                "expiry": utcnow() + timedelta(minutes=20),
                "unique_name": "#8",
            },
            {
                "guid": "tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9",
                version_id: "1",
                ITEM_TYPE: CONTENT_TYPE.TEXT,
                VERSION: 2,
                "urgency": 4,
                "headline": "Two students missing",
                "pubstatus": "usable",
                "firstcreated": utcnow(),
                "byline": "By Alan Karben",
                "dateline": {"located": {"city": "Sydney"}},
                "keywords": ["Student", "Crime", "Police", "Missing"],
                "subject": [{"qcode": "17004000", "name": "Statistics"}, {"qcode": "04001002", "name": "Weather"}],
                ITEM_STATE: CONTENT_STATE.SUBMITTED,
                "expiry": utcnow() + timedelta(minutes=20),
                "unique_name": "#8",
            },
            {
                "guid": "tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9",
                version_id: "1",
                ITEM_TYPE: CONTENT_TYPE.TEXT,
                VERSION: 3,
                "urgency": 4,
                "headline": "Two students missing",
                "pubstatus": "usable",
                "firstcreated": utcnow(),
                "byline": "By Alan Karben",
                "ednote": "Andrew Marwood contributed to this article",
                "dateline": {"located": {"city": "Sydney"}},
                "keywords": ["Student", "Crime", "Police", "Missing"],
                "subject": [{"qcode": "17004000", "name": "Statistics"}, {"qcode": "04001002", "name": "Weather"}],
                ITEM_STATE: CONTENT_STATE.PROGRESS,
                "expiry": utcnow() + timedelta(minutes=20),
                "unique_name": "#8",
            },
            {
                "guid": "tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9",
                version_id: "1",
                ITEM_TYPE: CONTENT_TYPE.TEXT,
                VERSION: 4,
                "body_html": "Test body",
                "urgency": 4,
                "headline": "Two students missing",
                "pubstatus": "usable",
                "firstcreated": utcnow(),
                "byline": "By Alan Karben",
                "ednote": "Andrew Marwood contributed to this article",
                "dateline": {"located": {"city": "Sydney"}},
                "keywords": ["Student", "Crime", "Police", "Missing"],
                "subject": [{"qcode": "17004000", "name": "Statistics"}, {"qcode": "04001002", "name": "Weather"}],
                ITEM_STATE: CONTENT_STATE.PROGRESS,
                "expiry": utcnow() + timedelta(minutes=20),
                "unique_name": "#8",
            },
        ]

    async def _is_publish_queue_empty(self):
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(0, len(queue_items))

    async def _add_content_filters(self, product: ProductsResource, is_global: bool = False) -> None:
        product.content_filter = ProductContentFilter(
            filter_id=FILTER_CONDITION_IDS[0], filter_type=ProductFilterType.BLOCKING
        )
        await test_utils.post_items(
            "filter_conditions",
            [
                {
                    "_id": FILTER_CONDITION_IDS[0],
                    "field": "headline",
                    "operator": "like",
                    "value": "tor",
                    "name": "test-1",
                }
            ],
        )
        await test_utils.post_items(
            "filter_conditions",
            [{"_id": FILTER_CONDITION_IDS[1], "field": "urgency", "operator": "in", "value": "2", "name": "test-2"}],
        )
        await test_utils.post_items(
            "filter_conditions",
            [
                {
                    "_id": FILTER_CONDITION_IDS[2],
                    "field": "headline",
                    "operator": "endswith",
                    "value": "tor",
                    "name": "test-3",
                }
            ],
        )
        await test_utils.post_items(
            "filter_conditions",
            [
                {
                    "_id": FILTER_CONDITION_IDS[3],
                    "field": "urgency",
                    "operator": "in",
                    "value": "2,3,4",
                    "name": "test-4",
                }
            ],
        )

        await test_utils.post_items(
            "content_filters",
            [
                {
                    "_id": CONTENT_FILTER_ID,
                    "name": "pf-1",
                    "is_global": is_global,
                    "content_filter": [
                        {"expression": {"fc": [FILTER_CONDITION_IDS[3], FILTER_CONDITION_IDS[2]]}},
                        {"expression": {"fc": [FILTER_CONDITION_IDS[0], FILTER_CONDITION_IDS[1]]}},
                    ],
                }
            ],
        )
        await PublishCache.init(force=True)

    async def test_publish(self):
        doc = self.articles[3].copy()
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc["_id"], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED}
        )
        published_doc = await get_resource_service(ARCHIVE).find_one_async(req=None, _id=doc["_id"])
        self.assertIsNotNone(published_doc)
        self.assertEqual(published_doc[VERSION], doc[VERSION] + 1)
        self.assertEqual(published_doc[ITEM_STATE], ArchivePublishService().published_state)

    async def test_versions_across_collections_after_publish(self):
        await test_utils.post_items("archive_versions", self.article_versions)

        # Publishing an Article
        doc = self.articles[3]
        original = doc.copy()

        published_version_number = original[VERSION] + 1
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc[ID_FIELD],
            updates={ITEM_STATE: CONTENT_STATE.PUBLISHED, VERSION: published_version_number},
        )

        article_in_production = await get_resource_service(ARCHIVE).find_one_async(req=None, _id=original[ID_FIELD])
        self.assertIsNotNone(article_in_production)
        self.assertEqual(article_in_production[ITEM_STATE], CONTENT_STATE.PUBLISHED)
        self.assertEqual(article_in_production[VERSION], published_version_number)

        lookup = {"item_id": original[ID_FIELD], "item_version": published_version_number}
        queue_items = await test_utils.find_many(PUBLISH_QUEUE, lookup)
        assert len(queue_items) > 0, "Transmission Details are empty for published item %s" % original[ID_FIELD]

        lookup = {"item_id": original[ID_FIELD], VERSION: published_version_number}
        request = ParsedRequest()
        request.args = {"aggregations": 0}
        items_in_published_collection = await (
            await get_resource_service(PUBLISHED).get_async(req=request, lookup=lookup)
        ).to_list()
        assert len(items_in_published_collection) > 0, "Item not found in published collection %s" % original[ID_FIELD]

    async def test_queue_transmission_for_item_scheduled_future(self):
        await self._is_publish_queue_empty()

        doc = copy(self.articles[5])
        doc["item_id"] = doc["_id"]
        schedule_date = utcnow() + timedelta(hours=2)
        updates = {"publish_schedule": schedule_date, "schedule_settings": {"utc_publish_schedule": schedule_date}}
        await get_resource_service(ARCHIVE).patch_async(id=doc["_id"], updates=updates)
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(id=doc["_id"], updates=updates)
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(0, len(queue_items))

    async def test_queue_transmission_for_item_scheduled_elapsed(self):
        await self._is_publish_queue_empty()

        doc = copy(self.articles[5])
        doc["item_id"] = doc["_id"]
        schedule_date = utcnow() + timedelta(minutes=10)
        updates = {"publish_schedule": schedule_date, "schedule_settings": {"utc_publish_schedule": schedule_date}}
        await get_resource_service(ARCHIVE).patch_async(id=doc["_id"], updates=updates)
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(id=doc["_id"], updates=updates)
        await self._is_publish_queue_empty()

        schedule_in_past = utcnow() + timedelta(minutes=-10)
        await get_resource_service(PUBLISHED).update_published_items(
            doc["_id"],
            {
                "schedule_settings": {"utc_publish_schedule": schedule_in_past},
                "publish_schedule": schedule_in_past,
            },
        )

        await enqueue_published()
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(1, len(queue_items))

    async def test_queue_transmission_for_digital_channels(self):
        await self._is_publish_queue_empty()

        doc = copy(self.articles[1])
        doc["item_id"] = doc["_id"]

        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc["_id"], updates={"target_media_type": SubscriberType.DIGITAL}
        )

        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(1, len(queue_items))
        expected_subscribers = [fixtures.subscribers.SUB5_ID]
        for item in queue_items:
            self.assertIn(item["subscriber_id"], expected_subscribers, "item {}".format(item))

    async def test_queue_transmission_for_wire_channels_with_codes(self):
        await self._is_publish_queue_empty()

        doc = copy(self.articles[1])
        doc["item_id"] = doc["_id"]

        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc["_id"], updates={"target_media_type": SubscriberType.WIRE}
        )
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))

        self.assertEqual(1, len(queue_items))
        expected_subscribers = [fixtures.subscribers.SUB5_ID]
        for item in queue_items:
            self.assertIn(item["subscriber_id"], expected_subscribers, "item {}".format(item))
            if item["subscriber_id"] == fixtures.subscribers.SUB5_ID:
                self.assertEqual(4, len(item["codes"]))
                self.assertIn("def", item["codes"])
                self.assertIn("abc", item["codes"])
                self.assertIn("xyz", item["codes"])
                self.assertIn("klm", item["codes"])

    async def test_get_subscribers_without_product(self):
        doc = copy(self.articles[1])
        # doc["item_id"] = doc["_id"]

        subscriber_service = SubscribersResource.get_service()
        await subscriber_service.delete_many({})

        for sub in self.subscribers:
            sub.products = []

        await subscriber_service.create(self.subscribers)
        await PublishCache.init(force=True)

        with self.assertRaises(SuperdeskApiError):
            # ``SuperdeskApiError.badRequestError`` is raised when item wasn't routed
            # This happens when no subscriber matched the item
            await get_resource_service(ARCHIVE_PUBLISH).patch_async(
                id=doc["_id"], updates={"target_media_type": SubscriberType.WIRE}
            )

        # There should be no items in the publish queue
        await self._is_publish_queue_empty()

    @markers.investigate_cause_of_error
    async def test_queue_transmission_wrong_article_type_fails(self):
        await self._is_publish_queue_empty()

        doc = copy(self.articles[1])
        doc["item_id"] = doc["_id"]
        doc[ITEM_TYPE] = CONTENT_TYPE.PICTURE

        # with self.assertRaises(SuperdeskApiError):
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc["_id"], updates={"target_media_type": SubscriberType.DIGITAL}
        )

        # service = get_enqueue_service(doc[ITEM_OPERATION])
        #
        # subscribers, subscriber_codes, associations = service.get_subscribers(doc, SUBSCRIBER_TYPES.DIGITAL)
        # queued = get_enqueue_service("publish").queue_transmission(doc, subscribers, subscriber_codes)
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(1, len(queue_items))
        # self.assertTrue(queued)

        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc["_id"], updates={"target_media_type": SubscriberType.WIRE}
        )

        # subscribers, subscriber_codes, associations = service.get_subscribers(doc, SUBSCRIBER_TYPES.WIRE)
        # queued = get_enqueue_service("publish").queue_transmission(doc, subscribers)
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(2, len(queue_items))
        # self.assertTrue(queued)

    async def test_delete_from_queue_by_article_id(self):
        await self._is_publish_queue_empty()

        doc = copy(self.articles[3])

        archive_publish = get_resource_service(ARCHIVE_PUBLISH)
        await archive_publish.patch_async(
            id=doc["_id"], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED, "target_media_type": SubscriberType.ALL}
        )

        await enqueue_published()
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(6, len(queue_items))

        # this will delete queue transmission for the wire article
        await get_resource_service(PUBLISHED).delete_by_article_id(doc["_id"])
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(0, len(queue_items))

    async def test_conform_target_regions(self):
        doc = {"_id": "test-article-1", "headline": "test"}
        product = ProductsResource(
            id=ObjectId(),
            name="QLD",
            geo_restrictions="QLD",
        )
        self.assertFalse(item_target_matches_product_target(doc, product))
        doc = {"_id": "test-article-1", "headline": "test", "target_regions": []}
        self.assertFalse(item_target_matches_product_target(doc, product))
        doc = {
            "_id": "test-article-1",
            "headline": "test",
            "target_regions": [{"qcode": "VIC", "name": "Victoria", "allow": True}],
        }
        self.assertFalse(item_target_matches_product_target(doc, product))
        doc = {
            "_id": "test-article-1",
            "headline": "test",
            "target_regions": [{"qcode": "VIC", "name": "Victoria", "allow": False}],
        }
        self.assertTrue(item_target_matches_product_target(doc, product))
        doc = {
            "_id": "test-article-1",
            "headline": "test",
            "target_regions": [{"qcode": "QLD", "name": "Queensland", "allow": True}],
        }
        self.assertTrue(item_target_matches_product_target(doc, product))
        doc = {
            "_id": "test-article-1",
            "headline": "test",
            "target_regions": [{"qcode": "QLD", "name": "Queensland", "allow": False}],
        }
        self.assertFalse(item_target_matches_product_target(doc, product))

    async def test_conform_target_subscribers(self):
        doc = {"_id": "test-article-1", "headline": "test"}
        subscriber = self.subscribers[0]

        self.assertTrue(item_target_matches_subscriber_target(doc, subscriber))
        doc.update({"target_subscribers": []})
        self.assertTrue(item_target_matches_subscriber_target(doc, subscriber))
        doc.update({"target_subscribers": [{"_id": fixtures.subscribers.SUB2_ID}]})
        self.assertFalse(item_target_matches_subscriber_target(doc, subscriber))

        doc.update({"target_subscribers": [{"_id": fixtures.subscribers.SUB1_ID}]})
        self.assertTrue(item_target_matches_subscriber_target(doc, subscriber))

        doc.update(
            {"target_subscribers": [{"_id": fixtures.subscribers.SUB2_ID}], "target_regions": [{"name": "Victoria"}]}
        )
        self.assertTrue(item_target_matches_subscriber_target(doc, subscriber))

    async def test_can_publish_article(self):
        product = self.products[0]
        await self._add_content_filters(product, is_global=False)

        can_it = item_matches_product_filters(self.articles[4], product)
        self.assertFalse(can_it)
        product.content_filter.filter_type = ProductFilterType.PERMITTING

        can_it = item_matches_product_filters(self.articles[4], product)
        self.assertTrue(can_it)

    async def test_can_publish_article_with_global_filters(self):
        subscriber = self.subscribers[0]
        product = self.products[0]
        await self._add_content_filters(product, is_global=True)

        article = self.articles[4]
        publish_request = PublishRequest(
            item=article,
            item_id=article["_id"],
            item_type=article.get("type") or "text",
            operation="publish",
            published_state="published",
        )
        self.filter.cache_global_filter_matches(publish_request)
        self.assertFalse(self.filter.subscriber_matches_global_filter(subscriber))

        subscriber.global_filters = {str(CONTENT_FILTER_ID): False}
        self.assertTrue(self.filter.subscriber_matches_global_filter(subscriber))

    async def test_is_targeted(self):
        doc = {"headline": "test"}
        self.assertFalse(BasePublishService().is_targeted(doc))
        doc = {"headline": "test", "target_regions": []}
        self.assertFalse(BasePublishService().is_targeted(doc))
        doc = {"headline": "test", "target_regions": [{"qcode": "NSW"}]}
        self.assertTrue(BasePublishService().is_targeted(doc))
        doc = {"headline": "test", "target_regions": [], "target_types": []}
        self.assertFalse(BasePublishService().is_targeted(doc))
        doc = {"headline": "test", "target_regions": [], "target_types": [{"qcode": "digital"}]}
        self.assertTrue(BasePublishService().is_targeted(doc))

    async def test_targeted_for_includes_digital_subscribers(self):
        updates = {"target_regions": [{"qcode": "NSW", "name": "New South Wales", "allow": True}]}
        doc_id = self.articles[5][ID_FIELD]
        await get_resource_service(ARCHIVE).patch_async(id=doc_id, updates=updates)

        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc_id, updates={ITEM_STATE: CONTENT_STATE.PUBLISHED, "target_media_type": SubscriberType.ALL}
        )
        await enqueue_published()
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(6, len(queue_items))
        expected_subscribers = [
            fixtures.subscribers.SUB1_ID,
            fixtures.subscribers.SUB2_ID,
            fixtures.subscribers.SUB3_ID,
            fixtures.subscribers.SUB4_ID,
            fixtures.subscribers.SUB5_ID,
        ]
        for item in queue_items:
            self.assertIn(item["subscriber_id"], expected_subscribers, "item {}".format(item))

    async def test_maintain_latest_version_for_published(self):
        async def get_publish_items(item_id, last_version):
            query = {
                "query": {
                    "filtered": {
                        "filter": {
                            "and": [{"term": {"item_id": item_id}}, {"term": {LAST_PUBLISHED_VERSION: last_version}}]
                        }
                    }
                }
            }
            request = ParsedRequest()
            request.args = {"source": json.dumps(query), "aggregations": 0}

            return await (await get_resource_service(PUBLISHED).get_async(req=request, lookup=None)).to_list()

        await get_resource_service(ARCHIVE).patch_async(
            id=self.articles[1][ID_FIELD], updates={"publish_schedule": None}
        )

        doc = await get_resource_service(ARCHIVE).find_one_async(req=None, _id=self.articles[1][ID_FIELD])
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc[ID_FIELD], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED}
        )

        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(1, len(queue_items))
        print(queue_items[0]["subscriber_id"])
        request = ParsedRequest()
        request.args = {"aggregations": 0}
        published_items = list(await test_utils.find_many(PUBLISHED))
        self.assertEqual(1, len(published_items))
        published_doc = next((item for item in published_items if item.get("item_id") == doc[ID_FIELD]), None)
        self.assertEqual(published_doc[LAST_PUBLISHED_VERSION], True)

        await get_resource_service(ARCHIVE_CORRECT).patch_async(
            id=doc[ID_FIELD], updates={ITEM_STATE: CONTENT_STATE.CORRECTED}
        )

        # TODO-ASYNC-PR: Fix this, for some reason there are 7 entries in the queue
        queue_items = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertEqual(2, len(queue_items))

        published_items = list(await test_utils.find_many(PUBLISHED))
        self.assertEqual(2, len(published_items))
        last_published = await get_publish_items(published_doc["item_id"], True)
        self.assertEqual(1, len(last_published))

    async def test_added_removed_in_a_package(self):
        package = {
            "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "123",
                            "headline": "item-1 headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123",
                        },
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "456",
                            "headline": "item-2 headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "456",
                        },
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "789",
                            "headline": "item-3 headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "789",
                        },
                    ],
                    "role": "grpRole:main",
                },
            ],
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "status": "todo",
                "stage": "#desks.incoming_stage#",
                "desk": "#desks._id#",
            },
            "guid": "compositeitem",
            "headline": "test package",
            "state": "submitted",
            "type": "composite",
        }

        updates = {
            "groups": [
                {"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "123",
                            "headline": "item-1 headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123",
                        },
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "555",
                            "headline": "item-2 headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "555",
                        },
                        {
                            "renditions": {},
                            "slugline": "Boat",
                            "guid": "456",
                            "headline": "item-2 headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "456",
                        },
                    ],
                    "role": "grpRole:main",
                },
            ],
            "task": {
                "user": "#CONTEXT_USER_ID#",
                "status": "todo",
                "stage": "#desks.incoming_stage#",
                "desk": "#desks._id#",
            },
            "guid": "compositeitem",
            "headline": "test package",
            "state": "submitted",
            "type": "composite",
        }

        items = PackageService().get_residrefs(package)
        removed_items, added_items = ArchivePublishService()._get_changed_items(items, updates)
        self.assertEqual(len(removed_items), 1)
        self.assertEqual(len(added_items), 1)

    async def test_get_changed_items_no_item_found(self):
        # dummy publishing so that elastic mappings are created.
        doc = self.articles[3].copy()
        await get_resource_service(ARCHIVE_PUBLISH).patch_async(
            id=doc["_id"], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED}
        )
        removed_items, added_items = get_resource_service(ARCHIVE_PUBLISH)._get_changed_items({}, {"item_id": "test"})
        self.assertEqual(len(removed_items), 0)
        self.assertEqual(len(added_items), 0)


class TimeoutTest(TestCase):
    published_items = [
        {
            "_id": ObjectId("58006b8d1d41c88eace5179d"),
            "item_id": "1",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "published",
            "operation": "publish",
        }
    ]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        init_app(self.app)

    # TODO-ASYNC-PR: Fix this mock/test to not use get_enqueue_service
    # This tests celery timeout, where as we're not using as much anymore
    # Need to figure out a way to test celery timeout, maybe force use of celery/polling?
    # @mock.patch("apps.publish.enqueue.get_enqueue_service", side_effect=SoftTimeLimitExceeded())
    @markers.investigate_cause_of_error
    async def test_soft_timeout_gets_re_queued(self):
        await test_utils.post_items("published", self.published_items)
        await enqueue_published()
        published = list(await test_utils.find_many(PUBLISH_QUEUE))
        self.assertTrue(published[0].get("queue_state"), "pending")
