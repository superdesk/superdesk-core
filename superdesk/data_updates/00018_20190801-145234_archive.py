# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2019-08-01 14:52

from superdesk import get_resource_service
from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'archive'

    def forwards(self, mongodb_collection, mongodb_database):
        for resource in ('archive', 'published'):
            service = get_resource_service(resource)
            for item in mongodb_database[resource].find({'type': 'text', 'associations': {'$gt': {}}}):
                update = False
                associations = {}
                for key, val in item['associations'].items():
                    if val and val.get('type') == 'text' and len(val.keys()) > 2:
                        update = True
                        associations[key] = {
                            '_id': val.get('item_id') or val.get('_id'),
                            'type': val['type'],
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
                    service.system_update(item['_id'], {'associations': associations}, item)

    def backwards(self, mongodb_collection, mongodb_database):
        pass
