# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : administrator
# Creation: 2021-02-12 00:28

from superdesk.commands.data_updates import BaseDataUpdate
from eve.utils import config


class DataUpdate(BaseDataUpdate):

    resource = "roles"

    def forwards(self, mongodb_collection, mongodb_database):
        for document in mongodb_collection.find({"privileges.planning_assignments_view": 1}):
            mongodb_collection.update(
                {"_id": document.get(config.ID_FIELD)}, {"$set": {"privileges.planning_assignments_desk": 1}}
            )

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
