# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Gyan
# Creation: 2018-12-27 16:03

from superdesk.commands.data_updates import DataUpdate
from eve.utils import config


# This script replaces the whole json of related item with respective _id only
class DataUpdate(DataUpdate):

    resource = 'archive'

    def forwards(self, mongodb_collection, mongodb_database):
        # To find the related content from vocabularies
        related_content = list(mongodb_database['vocabularies'].find({
            'field_type': 'related_content'
        }))

        collection = mongodb_database['archive']

        for item in collection.find({'associations': {'$ne': None}}):
            for item_name, item_obj in item['associations'].items():
                if item_obj and related_content:
                    if item_name.split('--')[0] in [content['_id'] for content in related_content]:
                        related_item_id = item_obj[config.ID_FIELD]

                        updates = {"$set": {}}
                        updates['$set']['associations.' + item_name] = {'_id': related_item_id}

                        print(collection.update({'_id': item['_id']}, updates))

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
