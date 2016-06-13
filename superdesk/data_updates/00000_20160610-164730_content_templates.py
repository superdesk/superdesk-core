# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : edouard
# Creation: 2016-06-10 11:10

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):
    """

    Data update for Pull Request #418

    SD-3487 As a user I want to be able to use a template in several desks
    https://github.com/superdesk/superdesk-core/pull/418


    Changes:

        1. `template_desks` added and is a list of desks, initialized with desk `template_desk`
        2. `template_stage` renamed by `schedule_stage`
        3. `template_desk` renamed by `schedule_desk`

    """

    resource = 'content_templates'

    def forwards(self, mongodb_collection, mongodb_database):
        # new `template_desks` field must contain a list of desk id
        for template in mongodb_collection.find({}):
            if template.get('template_desk'):
                print(mongodb_collection.update({'_id': template['_id']}, {
                    '$set': {
                        'template_desks': [template.get('template_desk')]
                    }
                }))
        # renames fields:
        #   - template_desk -> schedule_desk
        #   - template_stage -> schedule_stage
        print(mongodb_collection.update({}, {
            '$rename': {
                'template_desk': 'schedule_desk',
                'template_stage': 'schedule_stage'
            },
        }, upsert=False, multi=True))

    def backwards(self, mongodb_collection, mongodb_database):
        print(mongodb_collection.update({}, {
            '$rename': {
                'schedule_desk': 'template_desk',
                'schedule_stage': 'template_stage'
            },
        }, upsert=False, multi=True))
