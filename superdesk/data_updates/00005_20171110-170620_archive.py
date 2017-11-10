# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : mugur
# Creation: 2017-11-10 17:06

from superdesk.commands.data_updates import DataUpdate
from superdesk.commands.rebuild_elastic_index import RebuildElasticIndex


class DataUpdate(DataUpdate):

    resource = 'archive'

    def forwards(self, mongodb_collection, mongodb_database):
        RebuildElasticIndex()()

    def backwards(self, mongodb_collection, mongodb_database):
        pass
