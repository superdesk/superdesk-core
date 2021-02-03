# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Jérôme
# Creation: 2018-05-10 17:20

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):

    resource = "vocabularies"

    def forwards(self, mongodb_collection, mongodb_database):
        print(
            mongodb_collection.update_many(
                {"_id": {"$in": ["genre", "priority", "replace_words", "annotation_types"]}},
                {"$set": {"unique_field": "qcode"}},
            )
        )

    def backwards(self, mongodb_collection, mongodb_database):
        print(
            mongodb_collection.update_many(
                {"_id": {"$in": ["genre", "priority", "replace_words", "annotation_types"]}},
                {"$unset": {"unique_field": "qcode"}},
            )
        )
