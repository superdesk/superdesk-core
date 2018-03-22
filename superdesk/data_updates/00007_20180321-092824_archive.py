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


def get_updated_editor_state(editor_state):
    try:
        p1 = subprocess.Popen(["echo", json.dumps(editor_state)], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(
            [
                "node",
                join(dirname(realpath(superdesk.__file__)), "data_updates", "00007_20180321-092824_archive.dist.js")
            ],
            stdin=p1.stdout, stdout=subprocess.PIPE
        )

        p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
        output, err = p2.communicate()

        return json.loads(output.decode("utf-8"))

    except Exception:
        return editor_state


class DataUpdate(DataUpdate):

    resource = 'archive'

    def forwards(self, mongodb_collection, mongodb_database):
        return

        for item in mongodb_collection.find({'editor_state': {'$exists': True}}):

            print(mongodb_collection.update({'_id': item['_id']}, {
                '$set': {
                    'editor_state': get_updated_editor_state(item['editor_state'])
                }
            }))

    def backwards(self, mongodb_collection, mongodb_database):
        pass
