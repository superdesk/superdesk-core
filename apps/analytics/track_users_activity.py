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
            {"term": {"task.user": str(doc['user'])}}
        ]

        return terms

    def get_items(self, query):
        request = ParsedRequest()

        return get_resource_service('published').get(req=request, lookup=None)

    def count_items(self, query, option):
        my_list = self.get_items(query)
        items = sum(1 for i in my_list if i['state'] == option)

        return items

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
            no_of_processed_items = self.count_items(query, 'published')
            creation_date = t['firstcreated']
            last_modification_date = t['versioncreated']
            difference = str(abs(creation_date - last_modification_date))
            if t['state'] == 'published':
                info_list.append({'state': t['state'], 'item': t['_id'], 'time_to_complete': difference})

        return {'info': info_list, 'no_of_processed_items': no_of_processed_items}

    def create(self, docs):
        for doc in docs:
            doc['report'] = self.search_without_grouping(doc)
        docs = super().create(docs)
        return docs
