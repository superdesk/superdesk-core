# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2020-11-18 16:06

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'sequences'

    def forwards(self, mongodb_collection, mongodb_database):
        return mongodb_collection.delete_many({'key': None})

    def backwards(self, mongodb_collection, mongodb_database):
        pass
