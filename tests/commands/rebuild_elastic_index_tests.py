# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.tests import TestCase
from eve.utils import ParsedRequest
from superdesk import get_resource_service
from superdesk.commands.rebuild_elastic_index import RebuildElasticIndex


RESOURCE = 'ingest'


class RebuildIndexTestCase(TestCase):
    @property
    def data(self):
        return [
            {'headline': 'test {}'.format(i), 'slugline': 'rebuild {}'.format(i),
             'type': 'text' if (i % 2 == 0) else 'picture'} for i in range(11, 21)
        ]

    def query_items(self):
        req = ParsedRequest()
        req.args = {}
        req.max_results = 25
        return get_resource_service('ingest').get(req, {})

    async def test_retrieve_items_after_index_rebuilt(self):
        elastic = self.app.data.elastic
        alias = elastic._resource_index(RESOURCE)
        alias_info = elastic.elastic(RESOURCE).indices.get_alias(name=alias)

        get_resource_service(RESOURCE).post(self.data)
        RebuildElasticIndex().run()
        alias_info_new = elastic.elastic(RESOURCE).indices.get_alias(name=alias)
        self.assertNotEqual(alias_info, alias_info_new)

        items = self.query_items()
        self.assertEqual(10, items.count())

    async def test_rebuild_with_missing_index_wont_fail(self):
        elastic = self.app.data.elastic
        alias = elastic._resource_index(RESOURCE)
        index = elastic.get_index(RESOURCE)
        es = elastic.elastic(RESOURCE)
        es.indices.delete_alias(index, alias)
        es.indices.delete(index)

        RebuildElasticIndex().run(RESOURCE)

        assert es.indices.exists_alias(alias)

    async def test_rebuild_with_index_without_alias(self):
        elastic = self.app.data.elastic
        alias = elastic._resource_index(RESOURCE)
        index = elastic.get_index(RESOURCE)
        es = elastic.elastic(RESOURCE)
        es.indices.delete_alias(index, alias)
        es.indices.delete(index)

        es.indices.create(alias)
        get_resource_service(RESOURCE).post(self.data)

        RebuildElasticIndex().run(RESOURCE)

        assert es.indices.exists_alias(alias)

        items = self.query_items()
        self.assertEqual(10, items.count())
