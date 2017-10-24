# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : superdesk
# Creation: 2017-08-14 11:47

from superdesk.commands.data_updates import DataUpdate
from superdesk import get_resource_service
from eve.utils import config, app
from eve.io.mongo.mongo import create_index
from superdesk.audit.commands import PurgeAudit


class DataUpdate(DataUpdate):
    resource = 'audit'

    def forwards(self, mongodb_collection, mongodb_database):
        for audit in mongodb_collection.find({'resource': {'$in': PurgeAudit.item_resources}}):
            audit_id = get_resource_service(self.resource)._extract_doc_id(audit.get('extra'))
            print(mongodb_collection.update({'_id': audit.get(config.ID_FIELD)},
                                            {'$set': {
                                                'audit_id': audit_id
                                            }}))
        try:
            create_index(app=app, resource=self.resource, name='audit_id', list_of_keys=[('audit_id', 1)],
                         index_options={'background': True})
        except Exception:
            print('create index failed')

    def backwards(self, mongodb_collection, mongodb_database):
        print(mongodb_collection.update({},
                                        {'$unset': {'audit_id': []}},
                                        upsert=False, multi=True))
