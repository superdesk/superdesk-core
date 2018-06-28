# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : tomas
# Creation: 2018-06-18 09:04

from superdesk.commands.data_updates import DataUpdate
import json
from superdesk import json_utils


class DataUpdate(DataUpdate):

    resource = 'archive'  # will use multiple resources, keeping this here so validation passes

    def forwards(self, mongodb_collection, mongodb_database):
        for resource in ['archive', 'archive_autosave', 'published']:

            collection = mongodb_database[resource]

            for item in collection.find({'fields_meta': {"$gt": {}}}):

                try:
                    for field_meta_name in item.get('fields_meta', {}):

                        draft_js_state_wrapper = item['fields_meta'].get(field_meta_name, {}).get('draftjsState')

                        draft_js_state = None

                        if type(draft_js_state_wrapper) is dict:
                            draft_js_state = draft_js_state_wrapper
                        elif type(draft_js_state_wrapper) is list and len(draft_js_state_wrapper) == 1:
                            draft_js_state = draft_js_state_wrapper[0]
                        else:
                            continue

                        entity_map = draft_js_state.get('entityMap', {})

                        for entity_key in entity_map:
                            entity = entity_map[entity_key]
                            entity_data = entity.get('data', {}).get('data', {})
                            selector = entity_data.get('selector', None)

                            if(selector is not None and selector.startswith('#qumu')):
                                entity_map[entity_key] = {
                                    'type': 'EMBED',
                                    'mutability': 'MUTABLE',
                                    'data': {
                                        'data': {
                                            'html': '<script type="text/javascript"' +
                                            ' src="https://video.fidelity.tv/widgets/application.js">' +
                                            '</script><script type="text/javascript">' +
                                            'KV.widget(' + json.dumps(entity_data) + ');</script>'
                                        }
                                    }
                                }

                        print(collection.update({'_id': item['_id']}, {
                            '$set': {
                                'fields_meta.' + field_meta_name + '.draftjsState.0.entityMap': entity_map
                            }
                        }))
                except: # noqa E722 allow bare except
                    print('Exception occured while running an upgrade script 00013_20180618-090440_archive.py')
                    print('Find the offending item below:\n\n')
                    print(json_utils.dumps(item))
                    print('\n\n-- item end --\n\n')
                    raise

    def backwards(self, mongodb_collection, mongodb_database):
        pass
