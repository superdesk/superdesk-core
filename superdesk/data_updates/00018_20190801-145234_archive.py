# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2019-08-01 14:52

from bson import ObjectId
from bson.errors import InvalidId
from superdesk import get_resource_service
from superdesk.commands.data_updates import DataUpdate
from superdesk.vocabularies import is_related_content


class DataUpdate(DataUpdate):

    resource = 'archive'

    def forwards(self, mongodb_collection, mongodb_database):
        related = list(get_resource_service('vocabularies').get(req=None, lookup={'field_type': 'related_content'}))
        archive_service = get_resource_service('archive')
        for resource in ('archive', 'published'):
            service = get_resource_service(resource)
            for item in mongodb_database[resource].find({'type': 'text', 'associations': {'$gt': {}}}):
                update = False
                associations = {}
                for key, val in item['associations'].items():
                    if val and is_related_content(key, related) and len(val.keys()) > 2:
                        update = True
                        associations[key] = {
                            '_id': val['_id'],
                            'type': val.get('type', 'text'),
                        }
                    elif val and val.get('_id') and len(val.keys()) == 1:
                        type_ = mongodb_database[resource].find_one({'_id': val['_id']}, {'type': 1})
                        if type_:
                            update = True
                            associations[key] = val
                            associations[key]['type'] = type_['type']
                    else:
                        associations[key] = val
                if update:
                    try:
                        _id = ObjectId(item['_id'])
                    except InvalidId:
                        _id = item['_id']
                    # must update twice, otherwise it merges the changes
                    service.system_update(_id, {'associations': None}, item)
                    service.system_update(_id, {'associations': associations}, item)

    def backwards(self, mongodb_collection, mongodb_database):
        pass
