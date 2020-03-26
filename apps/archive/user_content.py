# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource, build_custom_hateoas
from superdesk.services import BaseService
from .common import CUSTOM_HATEOAS
from superdesk.metadata.utils import aggregations
from .archive import ArchiveResource
import superdesk


class UserContentResource(Resource):
    endpoint_name = 'user_content'
    item_url = ArchiveResource.item_url
    url = 'users/<regex("[a-f0-9]{24}"):original_creator>/content'
    schema = ArchiveResource.schema
    datasource = {
        'source': 'archive',
        'aggregations': aggregations,
        'elastic_filter': {
            'and': [
                {'not': {'exists': {'field': 'task.desk'}}},
                {'not': {'term': {'version': 0}}},
            ]
        }
    }
    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'PATCH', 'DELETE']
    resource_title = endpoint_name


class UserContentService(BaseService):

    def on_fetched(self, docs):
        """
        Overriding this to handle existing data in Mongo & Elastic
        """
        self.enhance_items(docs['_items'])

    def on_fetched_item(self, doc):
        self.enhance_items([doc])

    def enhance_items(self, items):
        for item in items:
            build_custom_hateoas(CUSTOM_HATEOAS, item)


superdesk.workflow_state('draft')
