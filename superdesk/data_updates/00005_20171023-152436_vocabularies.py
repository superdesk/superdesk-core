# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Jérôme
# Creation: 2017-10-23 15:24

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):

    resource = "vocabularies"

    def forwards(self, mongodb_collection, mongodb_database):
        print(
            mongodb_collection.update_many(
                {"_id": {"$in": ["author_roles", "job_titles"]}}, {"$set": {"unique_field": "qcode"}}
            )
        )

    def backwards(self, mongodb_collection, mongodb_database):
        print(
            mongodb_collection.update_many(
                {"_id": {"$in": ["author_roles", "job_titles"]}}, {"$unset": {"unique_field": "qcode"}}
            )
        )
