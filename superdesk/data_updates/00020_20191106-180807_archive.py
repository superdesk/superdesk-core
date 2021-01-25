# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Jérôme
# Creation: 2019-11-06 18:08

from superdesk.commands.data_updates import BaseDataUpdate
from superdesk import get_resource_service
from apps.archive.common import transtype_metadata
from datetime import datetime


class DataUpdate(BaseDataUpdate):

    resource = "archive"

    def forwards(self, mongodb_collection, mongodb_database):
        vocabularies_service = get_resource_service("vocabularies")
        cursor = vocabularies_service.find({"field_type": "date"})
        if cursor.count() == 0:
            print('No field with "date" type, there is nothing to do')
        else:
            for resource in ["archive", "archive_autosave", "published"]:

                collection = mongodb_database[resource]

                for item in collection.find({"extra": {"$exists": True, "$ne": {}}}):
                    transtype_metadata(item)
                    print(
                        collection.update(
                            {"_id": item["_id"]},
                            {
                                "$set": {"extra": item["extra"]},
                            },
                        )
                    )

    def backwards(self, mongodb_collection, mongodb_database):
        vocabularies_service = get_resource_service("vocabularies")
        cursor = vocabularies_service.find({"field_type": "date"})
        if cursor.count() == 0:
            print('No field with "date" type, there is nothing to do')
        else:
            for resource in ["archive", "archive_autosave", "published"]:

                collection = mongodb_database[resource]

                for item in collection.find({"extra": {"$exists": True, "$ne": {}}}):
                    extra = item["extra"]
                    for key, value in extra.items():
                        if isinstance(value, datetime):
                            extra[key] = value.isoformat()

                    print(
                        collection.update(
                            {"_id": item["_id"]},
                            {
                                "$set": {"extra": extra},
                            },
                        )
                    )
