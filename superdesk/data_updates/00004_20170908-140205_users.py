# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Jérôme
# Creation: 2017-09-08 14:02

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'users'

    def forwards(self, mongodb_collection, mongodb_database):
        # we want all existing users to be authors by default
        print(mongodb_collection.update_many({'is_author': {'$exists': False}},
                                             {'$set': {
                                                 'is_author': True
                                             }}))

    def backwards(self, mongodb_collection, mongodb_database):
        # author was not existing before the update, so we remove the value
        print(mongodb_collection.update_many({},
                                             {'$unset': {
                                                 'is_author': ''
                                             }}))
