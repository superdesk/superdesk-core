# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import superdesk
from superdesk.tests import TestCase
from apps.search_providers.service import SearchProviderService
from apps.search_providers import register_search_provider
from superdesk.errors import AlreadyExistsError


class SearchProviderTestCase(TestCase):
    def setUp(self):
        with self.app.app_context():
            self.service = SearchProviderService("search_providers", backend=superdesk.get_backend())
            try:
                register_search_provider("provider1", "provider1")
                register_search_provider("provider2", "provider2")
            except AlreadyExistsError:
                pass

    def test_set_is_default_on_create(self):
        with self.app.app_context():
            provider1 = {"search_provider": "provider1", "source": "provider1", "is_default": True}
            provider2 = {"search_provider": "provider2", "source": "provider2", "is_default": True}
            provider1_id = self.service.post([provider1])[0]
            provider2_id = self.service.post([provider2])[0]
            provider1 = self.service.find_one(req=None, _id=provider1_id)
            provider2 = self.service.find_one(req=None, _id=provider2_id)
            self.assertEqual(provider1["is_default"], False)
            self.assertEqual(provider2["is_default"], True)

    def test_set_is_default_on_update(self):
        with self.app.app_context():
            provider1 = {"search_provider": "provider1", "source": "provider1", "is_default": False}
            provider2 = {"search_provider": "provider2", "source": "provider2", "is_default": True}
            provider1_id = self.service.post([provider1])[0]
            provider2_id = self.service.post([provider2])[0]
            self.service.patch(provider1_id, {"is_default": True})
            provider1 = self.service.find_one(req=None, _id=provider1_id)
            provider2 = self.service.find_one(req=None, _id=provider2_id)
            self.assertEqual(provider1["is_default"], True)
            self.assertEqual(provider2["is_default"], False)
