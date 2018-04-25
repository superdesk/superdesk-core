# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : mugur
# Creation: 2018-04-25 01:07

from eve.utils import config
from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'vocabularies'
    update_fields = ['name', 'qcode']

    def forwards(self, mongodb_collection, mongodb_database):
        for vocabulary in mongodb_collection.find({}):
            if 'schema' in vocabulary:
                schema = vocabulary['schema']
                for field in self.update_fields:
                    if field in vocabulary['schema'] and type(vocabulary['schema']) == dict:
                        schema[field]['required'] = True
                mongodb_collection.update({'_id': vocabulary.get(config.ID_FIELD)},
                                          {'$set': {'schema': schema}})

    def backwards(self, mongodb_collection, mongodb_database):
        pass
