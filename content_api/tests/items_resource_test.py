# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from content_api.tests import ApiTestCase


class ItemsResourceTestCase(ApiTestCase):
    """Base class for the `items` resource tests."""

    def _get_target_class(self):
        """Return the class under test.

        Make the test fail immediately if the class cannot be imported.
        """
        try:
            from content_api.items import ItemsResource
        except ImportError:
            self.fail("Could not import class under test (ItemsResource).")
        else:
            return ItemsResource


class ResourceConfigTestCase(ItemsResourceTestCase):
    """Tests for the configuration of the `items` resource."""

    def test_datasource_filter_is_set_to_non_composite_types(self):
        klass = self._get_target_class()
        datasource = klass.datasource or {}
        filter_config = datasource.get("elastic_filter")
        self.assertEqual(filter_config, {"bool": {"must_not": {"term": {"type": "composite"}}}})

    def test_allowed_item_http_methods(self):
        klass = self._get_target_class()
        self.assertEqual(klass.item_methods, ["GET"])

    def test_allowed_resource_http_methods(self):
        klass = self._get_target_class()
        self.assertEqual(klass.resource_methods, ["GET"])
