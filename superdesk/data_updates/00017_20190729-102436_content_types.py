# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2019-07-29 10:24

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = 'content_types'

    def forwards(self, mongodb_collection, mongodb_database):
        filter_ = {'editor.headline.formatOptions': {'$nin': [None, []]}}
        update = {'$set': {'editor.headline.formatOptions': []}}
        result = mongodb_collection.update_many(filter_, update)
        print('matched={} updated={}'.format(result.matched_count, result.modified_count))

    def backwards(self, mongodb_collection, mongodb_database):
        pass  # no need to return back to wrong value
