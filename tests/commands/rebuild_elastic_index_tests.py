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
from time import sleep


class RebuildIndexTestCase(TestCase):

    def test_retrieve_items_after_index_rebuilt(self):
        RESOURCE = 'ingest'
        elastic = self.app.data.elastic
        alias = elastic._resource_index(RESOURCE)
        alias_info = elastic.elastic(RESOURCE).indices.get_alias(name=alias)

        data = [{'headline': 'test {}'.format(i), 'slugline': 'rebuild {}'.format(i),
                 'type': 'text' if (i % 2 == 0) else 'picture'} for i in range(11, 21)]
        get_resource_service(RESOURCE).post(data)
        RebuildElasticIndex().run()
        alias_info_new = elastic.elastic(RESOURCE).indices.get_alias(name=alias)
        self.assertNotEqual(alias_info, alias_info_new)

        req = ParsedRequest()
        req.args = {}
        req.max_results = 25
        items = get_resource_service('ingest').get(req, {})
        self.assertEqual(10, items.count())
