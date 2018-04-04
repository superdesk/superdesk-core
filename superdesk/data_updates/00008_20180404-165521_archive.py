# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Jérôme
# Creation: 2018-04-04 16:55

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'archive'  # will use multiple resources, keeping this here so validation passes

    def forwards(self, mongodb_collection, mongodb_database):
        for resource in ['archive', 'archive_autosave', 'published']:

            collection = mongodb_database[resource]

            for item in collection.find({'editor_state': {'$exists': True}}):
                state = item['editor_state']
                fields_meta = {'body_html': {'draftjsState': state}}
                print(collection.update({'_id': item['_id']}, {
                    '$set': {
                        'fields_meta': fields_meta
                    },
                    '$unset': {
                        'editor_state': ''
                    }
                }))

    def backwards(self, mongodb_collection, mongodb_database):
        for resource in ['archive', 'archive_autosave', 'published']:

            collection = mongodb_database[resource]

            for item in collection.find({'fields_meta': {'$exists': True}}):
                state = item['fields_meta']['body_html']['draftjsState']
                print(collection.update({'_id': item['_id']}, {
                    '$set': {
                        'editor_state': state
                    },
                    '$unset': {
                        'fields_meta': ''
                    }
                }))
