# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : tomas
# Creation: 2018-03-29 16:18

from superdesk.commands.data_updates import DataUpdate
    

class DataUpdate(DataUpdate):

    resource = 'archive'  # will use multiple resources, keeping this here so validation passes

    def forwards(self, mongodb_collection, mongodb_database):
        for resource in ['archive', 'archive_autosave', 'published']:

            collection = mongodb_database[resource]

            for item in collection.find({'editor_state': {'$exists': True}}):
                print(collection.update({'_id': item['_id']}, {
                    '$set': {
                        'fields_meta': {
                            'body_html': {
                                'draftjsState': item['editor_state']
                            }
                        }
                    },
                    '$unset': {
                        'editor_state': 1
                    }
                    
                }))

    def backwards(self, mongodb_collection, mongodb_database):
        pass
