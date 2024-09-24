# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : tomas
# Creation: 2024-09-24 12:34

from superdesk.commands.data_updates import BaseDataUpdate
from eve.utils import config

header_fields = [
    'slugline',
    'keywords',
    'genre',
    'anpa_take_key',
    'place',
    'language',
    'priority',
    'urgency',
    'anpa_category',
    'subject',
    'company_codes',
    'ednote',
    'authors',
]

class DataUpdate(BaseDataUpdate):
    resource = 'content_types'

    def forwards(self, mongodb_collection, mongodb_database):
        for profile in mongodb_collection.find({}):
            try:
                editor = profile.get("editor", {})
                for field, properties in editor.items():
                    if properties and "section" not in properties:
                        properties["section"] = 'header' if field in header_fields else 'content'

                mongodb_collection.update(
                    {"_id": profile.get(config.ID_FIELD)}, {"$set": {"editor": profile["editor"]}}
                )
                print(f"Content Profile {profile['_id']} updated successfully")
            except Exception as e:
                print(f"Error updating Content Profile {profile['_id']}: {str(e)}")

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
