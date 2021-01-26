# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : pablopunk
# Creation: 2020-09-09 14:08

from superdesk.commands.data_updates import BaseDataUpdate
from eve.utils import config


class DataUpdate(BaseDataUpdate):

    resource = "vocabularies"

    def forwards(self, mongodb_collection, mongodb_database):
        for vocabulary in mongodb_collection.find({"_id": "usageterms"}):
            if "schema_field" not in vocabulary:
                mongodb_collection.update(
                    {"_id": vocabulary.get(config.ID_FIELD)}, {"$set": {"schema_field": "usageterms"}}
                )

    def backwards(self, mongodb_collection, mongodb_database):
        pass
