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
from superdesk import config
import superdesk


class TrackActivityResource(Resource):
    """Track user's items schema
    """

    schema = {
        'user': metadata_schema['original_creator'],
        'desk': Resource.rel('desks', True)
    }

    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']

    privileges = {'POST': 'track_users_report', 'DELETE': 'track_users_report', 'GET': 'track_users_report'}


class TrackActivityService(BaseService):
    def create_query(self, doc):

        archive_version_query = {
                '$and': [
                    {'task.user': str(doc['user'])},
                    {'task.desk': str(doc['desk'])}
                ]
            }

        return archive_version_query

    def get_items(self, query):

        return get_resource_service('archive_versions').get(req=None, lookup=query)

    def search_without_grouping(self, doc):
        query = self.create_query(doc)
        items = superdesk.get_resource_service('archive_versions').get(req=None, lookup=query)

        # items_create = [i['_created'] for i in items if i['state'] == 'submitted']

        list_of_items = []
        for it in items:         
            elements = {'item_id': it['guid'], 'state': it['state'], 'stage': it['task'].get('stage')}
            list_of_items.append(elements)
        return {'info':list_of_items}

    def create(self, docs):
        for doc in docs:
            doc['report'] = self.search_without_grouping(doc)
        docs = super().create(docs)
        return docs
