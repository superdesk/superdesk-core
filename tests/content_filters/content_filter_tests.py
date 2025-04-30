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

from bson import ObjectId
from eve.utils import ParsedRequest

from superdesk.types import (
    ContentFiltersResource,
    SubscribersResource,
    VocabulariesResourceModel,
    FilterConditionsResource,
    FilterConditionOperator,
    ProductsResource,
    SubscriberType,
    ContentFilter,
    ContentFilterExpression,
)

from apps.prepopulate.app_populate import AppPopulateCommand
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.publish_async.publish_cache import PublishCache

from superdesk.publish_async.utils import (
    content_filter_to_elastic_query,
    item_matches_content_filter,
    get_content_filters_by_filter_condition,
)
from superdesk.publish_async.utils.content_filters import _get_content_filters_by_content_filter
from superdesk.publish_async.utils.subscribers import _get_subscribers_by_filter_condition

from superdesk.tests import TestCase

from .utils import content_filter_to_mongo_query


FILTER_CONDITION_IDS = [ObjectId(), ObjectId(), ObjectId(), ObjectId(), ObjectId(), ObjectId(), ObjectId()]
CONTENT_FILTER_IDS = [ObjectId(), ObjectId(), ObjectId(), ObjectId(), ObjectId(), ObjectId()]
PRODUCT_IDS = [ObjectId(), ObjectId()]
SUBSCRIBER_IDS = [ObjectId(), ObjectId()]


class ContentFilterTests(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.req = ParsedRequest()
        self.articles = [
            {"_id": "1", "urgency": 1, "headline": "story", "state": "fetched", "task": {"desk": 1}},
            {"_id": "2", "headline": "prtorque", "state": "fetched", "task": {"desk": 1}},
            {"_id": "3", "urgency": 3, "headline": "creator", "state": "fetched", "task": {"desk": 1}},
            {"_id": "4", "urgency": 4, "state": "fetched", "task": {"desk": 1}},
            {"_id": "5", "urgency": 2, "state": "fetched", "task": {"desk": 1}},
            {"_id": "6", "state": "fetched", "task": {"desk": 1}},
            {"_id": "7", "subject": [{"scheme": "my_vocabulary", "qcode": "MV:01"}], "task": {"desk": 1}},
            {"_id": "8", "extra": {"custom_text": "my text"}, "task": {"desk": 1}},
        ]
        self.app.data.insert("archive", self.articles)

        await VocabulariesResourceModel.get_service().create(
            [
                {
                    "_id": "my_vocabulary",
                    "display_name": "My Vocabulary",
                    "type": "manageable",
                    "field_type": None,
                    "schema": {"name": {}, "qcode": {}, "parent": {}},
                    "items": [{"name": "option 1", "qcode": "MV:01", "is_active": True}],
                },
                {
                    "_id": "custom_text",
                    "display_name": "Custom Text",
                    "type": "manageable",
                    "field_type": "text",
                    "items": [],
                },
            ]
        )

        self.filter_conditions_service = FilterConditionsResource.get_service()
        self.content_filters_service = ContentFiltersResource.get_service()
        self.products_service = ProductsResource.get_service()
        self.subscribers_service = SubscribersResource.get_service()

        await self.filter_conditions_service.create(
            [
                {
                    "_id": FILTER_CONDITION_IDS[0],
                    "field": "headline",
                    "operator": "like",
                    "value": "tor",
                    "name": "test-1",
                },
                {"_id": FILTER_CONDITION_IDS[1], "field": "urgency", "operator": "in", "value": "2", "name": "test-2"},
                {
                    "_id": FILTER_CONDITION_IDS[2],
                    "field": "headline",
                    "operator": "endswith",
                    "value": "tor",
                    "name": "test-3",
                },
                {
                    "_id": FILTER_CONDITION_IDS[3],
                    "field": "urgency",
                    "operator": "in",
                    "value": "2,3,4",
                    "name": "test-4",
                },
                {
                    "_id": FILTER_CONDITION_IDS[4],
                    "field": "headline",
                    "operator": "startswith",
                    "value": "sto",
                    "name": "test-5",
                },
                {
                    "_id": FILTER_CONDITION_IDS[5],
                    "field": "my_vocabulary",
                    "operator": "in",
                    "value": "MV:01",
                    "name": "test-6",
                },
                {
                    "_id": FILTER_CONDITION_IDS[6],
                    "field": "custom_text",
                    "operator": "eq",
                    "value": "my text",
                    "name": "test-7",
                },
            ]
        )

        await self.content_filters_service.create(
            [
                {
                    "_id": CONTENT_FILTER_IDS[0],
                    "content_filter": [{"expression": {"fc": [FILTER_CONDITION_IDS[0]]}}],
                    "name": "soccer-only",
                },
                {
                    "_id": CONTENT_FILTER_IDS[1],
                    "content_filter": [{"expression": {"fc": [FILTER_CONDITION_IDS[3], FILTER_CONDITION_IDS[2]]}}],
                    "name": "soccer-only2",
                },
                {
                    "_id": CONTENT_FILTER_IDS[2],
                    "content_filter": [
                        {"expression": {"pf": [CONTENT_FILTER_IDS[0]], "fc": [FILTER_CONDITION_IDS[1]]}}
                    ],
                    "name": "soccer-only3",
                },
                {
                    "_id": CONTENT_FILTER_IDS[3],
                    "content_filter": [
                        {"expression": {"fc": [FILTER_CONDITION_IDS[2]]}},
                        {"expression": {"fc": [FILTER_CONDITION_IDS[4]]}},
                    ],
                    "name": "soccer-only4",
                },
                {
                    "_id": CONTENT_FILTER_IDS[4],
                    "content_filter": [{"expression": {"fc": [FILTER_CONDITION_IDS[5]]}}],
                    "name": "my-vocabulary",
                },
                {
                    "_id": CONTENT_FILTER_IDS[5],
                    "content_filter": [{"expression": {"fc": [FILTER_CONDITION_IDS[6]]}}],
                    "name": "custom-text",
                },
            ]
        )

        await self.products_service.create(
            [
                {
                    "_id": PRODUCT_IDS[0],
                    "content_filter": {"filter_id": CONTENT_FILTER_IDS[2], "filter_type": "blocking"},
                    "name": "p-1",
                },
                {
                    "_id": PRODUCT_IDS[1],
                    "content_filter": {"filter_id": CONTENT_FILTER_IDS[0], "filter_type": "blocking"},
                    "name": "p-2",
                },
            ]
        )

        await self.subscribers_service.create(
            [
                {
                    "_id": SUBSCRIBER_IDS[0],
                    "products": [PRODUCT_IDS[0]],
                    "name": "sub1",
                    "subscriber_type": SubscriberType.ALL,
                    "email": "sub1@subscribers.org",
                },
                {
                    "_id": SUBSCRIBER_IDS[1],
                    "products": [PRODUCT_IDS[1]],
                    "name": "sub2",
                    "subscriber_type": SubscriberType.ALL,
                    "email": "sub2@subscribers.org",
                },
            ]
        )

        self.app.data.insert(
            "routing_schemes",
            [
                {
                    "_id": 1,
                    "name": "routing_scheme_1",
                    "rules": [
                        {
                            "filter": CONTENT_FILTER_IDS[3],
                            "name": "routing_rule_4",
                            "schedule": {
                                "day_of_week": ["MON"],
                                "hour_of_day_from": "0000",
                                "hour_of_day_to": "2355",
                            },
                            "actions": {"fetch": [], "publish": [], "exit": False},
                        }
                    ],
                }
            ],
        )


class RetrievingDataTests(ContentFilterTests):
    async def test_build_mongo_query_using_like_filter_single_fc(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]]))],
        )
        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(3, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("3" in doc_ids)

    async def test_build_mongo_query_using_like_filter_single_pf(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]]))],
        )
        query = await content_filter_to_mongo_query(doc)
        print(query)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(3, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("3" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_filter_condition(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]])),
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]])),
            ],
        )

        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(4, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("5" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_pf(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]])),
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]])),
            ],
        )
        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(4, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("5" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_filter_condition2(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[2], FILTER_CONDITION_IDS[3]])
                ),
            ],
        )
        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_pf2(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[1]])),
            ],
        )
        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_condition3(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[2], FILTER_CONDITION_IDS[3]])
                ),
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0], FILTER_CONDITION_IDS[1]])
                ),
            ],
        )
        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_pf3(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[1]])),
                ContentFilter(
                    expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]], fc=[FILTER_CONDITION_IDS[1]])
                ),
            ],
        )
        query = await content_filter_to_mongo_query(doc)
        docs = get_resource_service("archive").get_from_mongo(req=self.req, lookup=query)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_single_filter_condition(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]]))],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(3, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_single_content_filter(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]]))],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(3, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_multi_filter_condition(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]])),
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]])),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(4, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("3" in doc_ids)
        self.assertTrue("5" in doc_ids)

    async def test_build_mongo_query_using_like_filter_multi_content_filter(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]])),
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]])),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(4, docs.count())
        self.assertTrue("1" in doc_ids)
        self.assertTrue("2" in doc_ids)
        self.assertTrue("3" in doc_ids)
        self.assertTrue("5" in doc_ids)

    async def test_build_elastic_query_using_like_filter_multi_filter_condition2(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[2], FILTER_CONDITION_IDS[3]])
                ),
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0], FILTER_CONDITION_IDS[1]])
                ),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_multi_content_filter2(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[3], FILTER_CONDITION_IDS[2]])
                ),
                ContentFilter(
                    expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]], fc=[FILTER_CONDITION_IDS[1]])
                ),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_multi_content_filter3(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[1]])),
                ContentFilter(
                    expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]], fc=[FILTER_CONDITION_IDS[1]])
                ),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_multi_content_filter4(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[1]])),
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[2]])),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)

    async def test_build_elastic_query_using_like_filter_multi_content_filter5(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[3]], fc=[FILTER_CONDITION_IDS[3]])
                ),
            ],
        )
        query = {"query": {"filtered": {"query": await content_filter_to_elastic_query(doc)}}}
        self.req.args = {"source": json.dumps(query)}
        docs = get_resource_service("archive").get(req=self.req, lookup=None)
        doc_ids = [d["_id"] for d in docs]
        self.assertEqual(1, docs.count())
        self.assertTrue("3" in doc_ids)


class FilteringDataTests(ContentFilterTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await PublishCache.init(force=True)

    async def test_does_match_returns_true_for_nonexisting_filter(self):
        for article in self.articles:
            self.assertTrue(item_matches_content_filter(article, None))

    async def test_does_match_custom_vocabularies(self):
        doc1 = ContentFiltersResource(
            id=ObjectId(),
            name="mv-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[5]]))],
        )
        doc2 = ContentFiltersResource(
            id=ObjectId(),
            name="ct-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[6]]))],
        )
        self.assertTrue(item_matches_content_filter(self.articles[6], doc1))
        self.assertTrue(item_matches_content_filter(self.articles[7], doc2))

    async def test_does_match_using_like_filter_single_fc(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]]))],
        )

        self.assertTrue(item_matches_content_filter(self.articles[0], doc))
        self.assertTrue(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertFalse(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_single_pf(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]]))],
        )
        self.assertTrue(item_matches_content_filter(self.articles[0], doc))
        self.assertTrue(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertFalse(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_multi_fc(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0]])),
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]])),
            ],
        )
        self.assertTrue(item_matches_content_filter(self.articles[0], doc))
        self.assertTrue(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertTrue(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_multi_pf(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[0]])),
                ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[1]])),
            ],
        )
        self.assertTrue(item_matches_content_filter(self.articles[0], doc))
        self.assertTrue(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertTrue(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_multi_fc2(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[2], FILTER_CONDITION_IDS[3]])
                ),
            ],
        )
        self.assertFalse(item_matches_content_filter(self.articles[0], doc))
        self.assertFalse(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertFalse(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_multi_pf2(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[1]])),
            ],
        )
        self.assertFalse(item_matches_content_filter(self.articles[0], doc))
        self.assertFalse(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertFalse(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_multi_fc3(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[2], FILTER_CONDITION_IDS[3]])
                ),
                ContentFilter(
                    expression=ContentFilterExpression(fc=[FILTER_CONDITION_IDS[0], FILTER_CONDITION_IDS[1]])
                ),
            ],
        )
        self.assertFalse(item_matches_content_filter(self.articles[0], doc))
        self.assertFalse(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertFalse(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_does_match_using_like_filter_multi_pf3(self):
        doc = ContentFiltersResource(
            id=ObjectId(),
            name="pf-1",
            content_filter=[
                ContentFilter(
                    expression=ContentFilterExpression(pf=[CONTENT_FILTER_IDS[3]], fc=[FILTER_CONDITION_IDS[3]])
                ),
            ],
        )
        self.assertFalse(item_matches_content_filter(self.articles[0], doc))
        self.assertFalse(item_matches_content_filter(self.articles[1], doc))
        self.assertTrue(item_matches_content_filter(self.articles[2], doc))
        self.assertFalse(item_matches_content_filter(self.articles[3], doc))
        self.assertFalse(item_matches_content_filter(self.articles[4], doc))
        self.assertFalse(item_matches_content_filter(self.articles[5], doc))

    async def test_if_pf_is_used(self):
        self.assertEqual(1, len(await _get_content_filters_by_content_filter(CONTENT_FILTER_IDS[0])))
        self.assertEqual(0, len(await _get_content_filters_by_content_filter(CONTENT_FILTER_IDS[4])))

    async def test_if_fc_is_used(self):
        self.assertEqual(len(await get_content_filters_by_filter_condition(FILTER_CONDITION_IDS[0])), 2)
        self.assertEqual(len(await get_content_filters_by_filter_condition(FILTER_CONDITION_IDS[2])), 2)
        self.assertEqual(len(await get_content_filters_by_filter_condition(FILTER_CONDITION_IDS[1])), 1)

    async def test_get_subscribers_by_filter_condition(self):
        filter_condition1 = {"field": "urgency", "operator": "in", "value": "2"}
        filter_condition2 = {"field": "urgency", "operator": "in", "value": "1"}
        filter_condition3 = {"field": "headline", "operator": "like", "value": "tor"}
        filter_condition4 = {"field": "urgency", "operator": "nin", "value": "3"}

        cmd = AppPopulateCommand()
        filename = os.path.join(
            os.path.abspath(os.path.dirname("apps/prepopulate/data_init/vocabularies.json")), "vocabularies.json"
        )
        await cmd.run(filename)
        r1 = await _get_subscribers_by_filter_condition(filter_condition1)
        r2 = await _get_subscribers_by_filter_condition(filter_condition2)
        r3 = await _get_subscribers_by_filter_condition(filter_condition3)
        r4 = await _get_subscribers_by_filter_condition(filter_condition4)
        self.assertEqual(len(r1["selected_subscribers"]), 1)
        self.assertEqual(len(r2["selected_subscribers"]), 0)
        self.assertEqual(len(r3["selected_subscribers"]), 2)
        self.assertEqual(len(r4["selected_subscribers"]), 1)

    async def test_does_match_return_with_caching_mechanism(self):
        filter_condition_id = ObjectId()
        await self.filter_conditions_service.create(
            [
                FilterConditionsResource(
                    id=filter_condition_id,
                    operator=FilterConditionOperator.IN,
                    field="my_vocabulary",
                    value="BIN/ALG",
                    name="Bin/alg filter_c",
                )
            ]
        )
        content_filter = ContentFiltersResource(
            id=ObjectId(),
            name="Bin/ALG Filter",
            content_filter=[
                ContentFilter(expression=ContentFilterExpression(fc=[filter_condition_id])),
            ],
        )
        await self.content_filters_service.create([content_filter])

        # If there are changes in the filters, we **must** re-init the cache
        await PublishCache.init(force=True)

        item = {
            "_id": "urn:newsml:localhost:5000:2019-12-10T14:43:46.224107:d13ac5ae-7f43-4b7f-89a5-2c6835389564",
            "guid": "urn:newsml:localhost:5000:2019-12-10T14:43:46.224107:d13ac5ae-7f43-4b7f-89a5-2c6835389564",
            "subject": [
                {
                    "name": "BIN/ALG",
                    "qcode": "BIN/ALG",
                    "parent": "BIN",
                    "scheme": "my_vocabulary",
                },
            ],
        }

        self.assertTrue(item_matches_content_filter(item, content_filter))

        # Modified Item data
        item["subject"] = [
            {
                "name": "BIN/ECO",
                "qcode": "BIN/ECO",
                "parent": "BIN",
                "scheme": "my_vocabulary",
            },
        ]

        # Test with cached data
        self.assertTrue(item_matches_content_filter(item, content_filter))

        # Reset cache and try again
        await PublishCache.init(force=True)
        self.assertFalse(item_matches_content_filter(item, content_filter))


class DeleteMethodTestCase(ContentFilterTests):
    """Tests for the delete() method."""

    async def test_raises_error_if_filter_referenced_by_subscribers(self):
        content_filter = await self.content_filters_service.find_by_id(CONTENT_FILTER_IDS[0])
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self.content_filters_service.delete(content_filter)

        self.assertEqual(ctx.exception.status_code, 400)  # bad request error

    async def test_raises_error_if_filter_referenced_by_routing_rules(self):
        content_filter = await self.content_filters_service.find_by_id(CONTENT_FILTER_IDS[3])
        with self.assertRaises(SuperdeskApiError) as ctx:
            await self.content_filters_service.delete(content_filter)

        self.assertEqual(ctx.exception.status_code, 400)  # bad request error
