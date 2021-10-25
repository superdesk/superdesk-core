# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : rails
# Creation: 2021-03-05 13:23

from superdesk import get_resource_service
from superdesk.commands.data_updates import BaseDataUpdate
from eve.utils import config


class DataUpdate(BaseDataUpdate):

    resource = "contacts"

    def forwards(self, mongodb_collection, mongodb_database):
        regions = get_resource_service("vocabularies").find_one(req=None, _id="regions")
        for document in mongodb_collection.find({"contact_state": {"$exists": True}}):
            if document.get("contact_state") and regions:
                region = [t for t in regions.get("items") if t.get("name") == document["contact_state"]]
                if region:
                    contact_state = {
                        "contact_state": {
                            "name": region[0].get("name"),
                            "qcode": region[0].get("qcode"),
                            "translations": region[0].get("translations"),
                        }
                    }
                else:
                    contact_state = {
                        "contact_state": {
                            "name": document["contact_state"],
                            "qcode": document["contact_state"],
                        }
                    }
                mongodb_collection.update(
                    {"_id": document.get(config.ID_FIELD)},
                    {"$set": contact_state},
                )

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
