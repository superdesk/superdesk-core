# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : mugur
# Creation: 2018-05-24 00:41

from eve.utils import config
from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'vocabularies'

    def forwards(self, mongodb_collection, mongodb_database):
        for vocabulary in mongodb_collection.find({}):
            changed = False
            if 'items' in vocabulary:
                for item in vocabulary['items']:
                    for field in ['name', 'qcode']:
                        if field in item and type(item[field]) == int:
                            item[field] = str(item[field])
                            changed = True
            if changed:
                mongodb_collection.update({'_id': vocabulary.get(config.ID_FIELD)},
                                          {'$set': {'items': vocabulary['items']}})

    def backwards(self, mongodb_collection, mongodb_database):
        pass
