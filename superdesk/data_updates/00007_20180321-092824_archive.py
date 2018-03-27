# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : tomas
# Creation: 2018-03-21 09:28

import superdesk
import subprocess
import json
from superdesk.commands.data_updates import DataUpdate
from os.path import realpath, join, dirname

node_script_path = join(dirname(realpath(superdesk.__file__)), "data_updates", "00007_20180321-092824_archive.dist.js")


def get_updated_editor_state(editor_state):
    try:
        with subprocess.Popen(['node', node_script_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as p:
            output, err = p.communicate(bytes(json.dumps(editor_state), 'utf-8'))
            return json.loads(output.decode('utf-8'))
    except Exception:
        return editor_state


class DataUpdate(DataUpdate):

    resource = 'archive'  # will use multiple resources, keeping this here so validation passes

    def forwards(self, mongodb_collection, mongodb_database):
        for resource in ['archive', 'archive_autosave', 'published']:

            collection = mongodb_database[resource]

            for item in collection.find({'editor_state': {'$exists': True}}):
                print(collection.update({'_id': item['_id']}, {
                    '$set': {
                        'editor_state': get_updated_editor_state(item['editor_state'])
                    }
                }))

    def backwards(self, mongodb_collection, mongodb_database):
        pass
