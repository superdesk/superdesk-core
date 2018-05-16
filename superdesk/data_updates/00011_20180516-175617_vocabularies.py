# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Jérôme
# Creation: 2018-05-16 17:56

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'vocabularies'

    def forwards(self, mongodb_collection, mongodb_database):
        print(mongodb_collection.update_many({'unique_field': {'$exists': False},
                                              'schema.qcode': {'$exists': True}},
                                             {'$set': {
                                                 'unique_field': "qcode"
                                             }}))

    def backwards(self, mongodb_collection, mongodb_database):
        pass
