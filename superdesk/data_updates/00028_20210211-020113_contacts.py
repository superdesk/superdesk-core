# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : administrator
# Creation: 2021-02-10 18:44

from superdesk import get_resource_service
from superdesk.commands.data_updates import BaseDataUpdate
from eve.utils import config


class DataUpdate(BaseDataUpdate):

    resource = "contacts"

    def forwards(self, mongodb_collection, mongodb_database):
        countries = get_resource_service("vocabularies").find_one(req=None, _id="countries")
        for document in mongodb_collection.find({"country": {"$exists": True}}):
            if document.get("country") and countries:
                country = [t for t in countries.get("items") if t.get("name") == document["country"]]
                if country:
                    mongodb_collection.update(
                        {"_id": document.get(config.ID_FIELD)},
                        {
                            "$set": {
                                "country": {
                                    "name": country[0].get("name"),
                                    "qcode": country[0].get("qcode"),
                                    "translations": country[0].get("translations"),
                                }
                            }
                        },
                    )

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
