# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : sdesk
# Creation: 2016-07-22 11:16

from superdesk.commands.data_updates import DataUpdate
from superdesk import get_resource_service
from eve.utils import config


class DataUpdate(DataUpdate):
    """Updates the user collection with invisible stages.

    Refer to https://dev.sourcefabric.org/browse/SD-5077 for more information
    """

    resource = 'users'

    def forwards(self, mongodb_collection, mongodb_database):
        for user in mongodb_collection.find({}):
            stages = get_resource_service(self.resource).get_invisible_stages_ids(user.get(config.ID_FIELD))
            print(mongodb_collection.update({'_id': user.get(config.ID_FIELD)},
                                            {'$set': {
                                                'invisible_stages': stages
                                            }}))

    def backwards(self, mongodb_collection, mongodb_database):
        print(mongodb_collection.update({},
                                        {'$unset': {'invisible_stages': []}},
                                        upsert=False, multi=True))
