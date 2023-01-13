# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : calculated
# Creation: 2023-01-13 14:10

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):

    resource = 'desks'

    def forwards(self, mongodb_collection, mongodb_database):
        print(
            mongodb_collection.update_many({}, {"$set": {"send_to_desk_allowed": True}})
        )

    def backwards(self, mongodb_collection, mongodb_database):
        print(
            mongodb_collection.update_many({}, {"$unset": {"send_to_desk_allowed": True}})
        )
