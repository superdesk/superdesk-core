# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : mugur
# Creation: 2018-06-05 15:10

from eve.utils import config
from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):

    resource = "vocabularies"

    def forwards(self, mongodb_collection, mongodb_database):
        for vocabulary in mongodb_collection.find({"_id": {"$in": ["priority", "urgency"]}}):
            schema = vocabulary.get("schema", {})
            qcode = schema.get("qcode", {})
            qcode["type"] = "integer"
            schema["qcode"] = qcode
            print(mongodb_collection.update({"_id": vocabulary.get(config.ID_FIELD)}, {"$set": {"schema": schema}}))

    def backwards(self, mongodb_collection, mongodb_database):
        pass
