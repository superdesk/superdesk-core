# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from unittest import mock
from unittest.mock import MagicMock
from flask import Flask
from werkzeug.datastructures import MultiDict
from content_api.tests import ApiTestCase


class SearchServiceTestCase(ApiTestCase):
    """Base class for the `items` service tests."""

    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.test_request_context("/")
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def _get_target_class(self):
        """Return the class under test.

        Make the test fail immediately if the class cannot be imported.
        """
        try:
            from content_api.search import SearchService
        except ImportError:
            self.fail("Could not import class under test (SearchService).")
        else:
            return SearchService

    def _make_one(self, *args, **kwargs):
        """Create a new instance of the class under test."""
        return self._get_target_class()(*args, **kwargs)


fake_super_get = MagicMock(name="fake super().get")


@mock.patch("content_api.items.service.BaseService.get", fake_super_get)
class MapResponseTestCast(SearchServiceTestCase):
    def test_format_cv(self):
        instance = self._make_one()
        item = instance._format_cv_item({"code": "x", "name": "test"})
        self.assertEqual(item["qcode"], "x")

    def test_map_item(self):
        instance = self._make_one()
        item = {
            "service": [{"code": "x", "name": "foo"}],
            "genre": [{"code": "y", "name": "bar"}],
            "subject": [{"code": "a", "name": "xyz"}],
            "place": [{"code": "a", "name": "xyz"}],
            "headline": "headline",
        }

        instance._map_item(item)

        expected = {
            "anpa_category": [{"qcode": "x", "name": "foo"}],
            "genre": [{"qcode": "y", "name": "bar"}],
            "subject": [{"qcode": "a", "name": "xyz"}],
            "place": [{"qcode": "a", "name": "xyz"}],
            "headline": "headline",
        }

        self.assertEqual(item, expected)

    def test_aggregations(self):
        fake_request = MagicMock()
        fake_request.args = MultiDict([("aggregations", 1)])
        lookup = {}
        fake_response = MagicMock()
        fake_response.count.return_value = 1
        fake_super_get.return_value = fake_response

        instance = self._make_one()
        instance.get(fake_request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args

        self.assertGreater(len(args), 0)
        self.assertEqual(args[0].args["aggregations"], 1)

        fake_request = MagicMock()
        fake_request.args = MultiDict([("aggregations", 0)])
        lookup = {}

        instance = self._make_one()
        instance.get(fake_request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args

        self.assertGreater(len(args), 0)
        self.assertEqual(args[0].args["aggregations"], 0)
