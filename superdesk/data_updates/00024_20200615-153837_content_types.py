# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2020-06-15 15:38

import superdesk

from flask import current_app as app
from werkzeug.exceptions import Conflict
from superdesk.commands.data_updates import DataUpdate
from superdesk.default_schema import DEFAULT_SCHEMA, DEFAULT_EDITOR


def filter_body_fields(config):
    return {
        key: val for key, val in config.items() if not key.startswith('body_')
    }


class DataUpdate(DataUpdate):

    resource = 'content_types'

    def forwards(self, mongodb_collection, mongodb_database):
        # set type for existing profiles to text
        print(
            'updated existing profiles',
            mongodb_collection.update_many({'item_type': None}, {'$set': {'item_type': 'text'}}).modified_count,
        )
        default_schema = filter_body_fields(DEFAULT_SCHEMA)
        default_editor = filter_body_fields(DEFAULT_EDITOR)
        # generate new types based on core conf
        for item_type in ('text', 'audio', 'video', 'picture', 'composite'):
            try:
                schema = app.config['SCHEMA'][item_type]
            except KeyError:
                schema = DEFAULT_SCHEMA.copy()
                if item_type != 'text':
                    schema = filter_body_fields(schema)
            try:
                editor = app.config['EDITOR'][item_type]
            except KeyError:
                editor = DEFAULT_EDITOR.copy()
                if item_type != 'text':
                    editor = filter_body_fields(editor)
            profile = {
                '_id': item_type,
                'label': item_type,
                'item_type': item_type,
                'schema': schema,
                'editor': editor,
                'enabled': True,
                'is_used': True,
            }

            try:
                print('creating content profile for', item_type)
                superdesk.get_resource_service(self.resource).create([profile])
            except Conflict:
                print('profile already existed for', item_type)

        desks = list(superdesk.get_resource_service('desks').find({'default_content_template': None}))
        if desks:
            superdesk.get_resource_service('content_templates').create([{
                'data': {'profile': 'text', 'type': 'text'},
                'template_name': 'Plain Text',
                'template_type': 'create',
                'template_desks': [desk['_id'] for desk in desks],
                'is_public': True,
            }])

    def backwards(self, mongodb_collection, mongodb_database):
        pass
