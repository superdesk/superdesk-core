# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from superdesk.services import BaseService

from eve.utils import ParsedRequest
from superdesk.metadata.item import metadata_schema
from superdesk.resource import Resource
import json


class TrackActivityResource(Resource):
    """Track user's items schema
    """

    schema = {
        'user': metadata_schema['original_creator']
    }

    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']

    privileges = {'POST': 'track_users_report', 'DELETE': 'track_users_report', 'GET': 'track_users_report'}


class TrackActivityService(BaseService):
    def create_query(self, doc):
        terms = [
            {"term": {"original_creator": str(doc['user'])}}
        ]

        return terms

    def get_items(self, query):
        request = ParsedRequest()
        request.args = {'source': json.dumps(query), 'repo': 'archive, published'}

        return get_resource_service('archive').get(req=request, lookup=None)

    def search_without_grouping(self, doc):
        terms = self.create_query(doc)
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {"must": terms}
                    }
                }
            }
        }

        all_items = self.get_items(query)
        info_list = []
        for t in all_items:
            creation_date = t['_created']
            last_modification_date = t['versioncreated']
            difference = str(abs(creation_date - last_modification_date))
            info_list.append({'state': t['state'], 'item': t['_id'], 'time_to_complete': difference})

        return {'no_of_items': self.get_items(query).count(), 'info': info_list}

    def create(self, docs):
        for doc in docs:
            doc['report'] = self.search_without_grouping(doc)
        docs = super().create(docs)
        return docs
