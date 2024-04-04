# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2024-04-04 12:30

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):
    resource = "content_types"

    def forwards(self, mongodb_collection, mongodb_database):
        mongodb_collection.update_many(
            {"type": {"$exists": False}, "_id": {"$nin": ["text", "picture", "video", "audio"]}},
            {
                "$set": {
                    "type": "text",
                },
            },
        )

    def backwards(self, mongodb_collection, mongodb_database):
        mongodb_collection.update_many(
            {"type": "text"},
            {
                "$unset": {
                    "type": 1,
                },
            },
        )
