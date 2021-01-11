# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json
from eve.utils import ParsedRequest
from superdesk.tests import TestCase
from superdesk import get_resource_service


class ElasticSearchSettingsTest(TestCase):
    items = [
        {"_id": "123", "headline": "Test 1", "slugline": "Soccer England", "body_html": "Test"},
        {"_id": "456", "headline": "Test 2", "slugline": "Soccer England Result", "body_html": "Test"},
        {"_id": "489", "headline": "Test 3", "slugline": "Soccer-England/Result", "body_html": "Test"},
        {"_id": "321", "headline": "Test 4", "slugline": "Test Soccer England", "body_html": "Test"},
        {"_id": "654", "headline": "Test 5", "slugline": "England Test Soccer", "body_html": "Test"},
        {"_id": "984", "headline": "Test 6", "slugline": "Soccer Germany", "body_html": "Test"},
    ]

    def setUp(self):
        get_resource_service("ingest").post(self.items)

    def test_query_prefix_soccer(self):
        query = {"query": {"filtered": {"query": {"match_phrase_prefix": {"slugline.phrase": "soccer"}}}}}

        req = ParsedRequest()
        req.args = {"source": json.dumps(query)}
        query_result = get_resource_service("ingest").get(req=req, lookup=None)
        self.assertEqual(query_result.count(), 4)
        sluglines = [item.get("slugline") for item in query_result]
        self.assertIn("Soccer Germany", sluglines)
        self.assertIn("Soccer-England/Result", sluglines)
        self.assertIn("Soccer England", sluglines)
        self.assertIn("Soccer England Result", sluglines)

    def test_query_prefix_soccer_england(self):
        query = {"query": {"filtered": {"query": {"match_phrase_prefix": {"slugline.phrase": "soccer england"}}}}}

        req = ParsedRequest()
        req.args = {"source": json.dumps(query)}
        query_result = get_resource_service("ingest").get(req=req, lookup=None)
        self.assertEqual(query_result.count(), 3)
        sluglines = [item.get("slugline") for item in query_result]
        self.assertIn("Soccer-England/Result", sluglines)
        self.assertIn("Soccer England", sluglines)
        self.assertIn("Soccer England Result", sluglines)

    def test_query_prefix_soccer_england_result_without_forward_slash(self):
        query = {
            "query": {"filtered": {"query": {"match_phrase_prefix": {"slugline.phrase": "soccer-england result"}}}}
        }

        req = ParsedRequest()
        req.args = {"source": json.dumps(query)}
        query_result = get_resource_service("ingest").get(req=req, lookup=None)
        self.assertEqual(query_result.count(), 1)
        sluglines = [item.get("slugline") for item in query_result]
        self.assertIn("Soccer England Result", sluglines)

    def test_query_prefix_soccer_england_result_with_forward_slash(self):
        query = {
            "query": {"filtered": {"query": {"match_phrase_prefix": {"slugline.phrase": "soccer england/result"}}}}
        }

        req = ParsedRequest()
        req.args = {"source": json.dumps(query)}
        query_result = get_resource_service("ingest").get(req=req, lookup=None)
        self.assertEqual(query_result.count(), 1)
        sluglines = [item.get("slugline") for item in query_result]
        self.assertIn("Soccer-England/Result", sluglines)
