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


class PackagesResourceTestCase(ApiTestCase):
    """Base class for the `packages` resource tests."""

    def _get_target_class(self):
        """Return the class under test.

        Make the test fail immediately if the class cannot be imported.
        """
        try:
            from content_api.packages import PackagesResource
        except ImportError:
            self.fail("Could not import class under test (PackagesResource).")
        else:
            return PackagesResource


class ResourceConfigTestCase(PackagesResourceTestCase):
    """Tests for the configuration of the `packages` resource."""

    def test_datasource_filter_is_set_to_composite_types(self):
        klass = self._get_target_class()
        datasource = klass.datasource or {}
        filter_config = datasource.get("elastic_filter")
        self.assertEqual(filter_config, {"bool": {"must": {"term": {"type": "composite"}}}})

    def test_allowed_item_http_methods(self):
        klass = self._get_target_class()
        self.assertEqual(klass.item_methods, ["GET"])

    def test_allowed_resource_http_methods(self):
        klass = self._get_target_class()
        self.assertEqual(klass.resource_methods, ["GET"])
