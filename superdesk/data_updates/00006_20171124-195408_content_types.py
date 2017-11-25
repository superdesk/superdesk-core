# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : mugur
# Creation: 2017-11-24 19:54

from copy import deepcopy
from superdesk.commands.data_updates import DataUpdate

from eve.utils import config


class DataUpdate(DataUpdate):
    replace_values_forward = {
        'picture': 'media',
        'unorderedlist': 'unordered list',
        'orderedlist': 'ordered list',
        'anchor': 'link',
        'removeFormat': None
    }
    replace_values_backward = {
        'media': 'picture',
        'unordered list': 'unorderedlist',
        'ordered list': 'orderedlist',
        'link': 'anchor'
    }

    resource = 'content_types'

    def forwards(self, mongodb_collection, mongodb_database):
        self._process_content_type(mongodb_collection, self.replace_values_forward)

    def backwards(self, mongodb_collection, mongodb_database):
        self._process_content_type(self.replace_values_backward)

    def _process_content_type(self, mongodb_collection, replace_values):
        for content_type in mongodb_collection.find({}):
            if 'editor' not in content_type:
                continue
            original_editor = deepcopy(content_type['editor'])
            for field, description in content_type['editor'].items():
                if description and description.get('formatOptions'):
                    for original, new in replace_values.items():
                        if original in description['formatOptions']:
                            description['formatOptions'].remove(original)
                            if new:
                                description['formatOptions'].append(new)
            if original_editor != content_type['editor']:
                print('update editor in content type', content_type['label'])
                mongodb_collection.update({'_id': content_type.get(config.ID_FIELD)},
                                          {'$set': {
                                              'editor': content_type['editor']
                                          }})
