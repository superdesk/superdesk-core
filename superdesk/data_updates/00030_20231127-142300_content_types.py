# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Ketan
# Creation: 2023-11-27 14:23

from superdesk.commands.data_updates import BaseDataUpdate
from superdesk.resource_fields import ID_FIELD


class DataUpdate(BaseDataUpdate):
    resource = "content_types"

    def forwards(self, mongodb_collection, mongodb_database):
        for profile in mongodb_collection.find({}):
            try:
                editor = profile.get("editor", {})
                for field, properties in editor.items():
                    if properties and "sdWidth" not in properties:
                        properties["sdWidth"] = "full"

                mongodb_collection.update({"_id": profile.get(ID_FIELD)}, {"$set": {"editor": profile["editor"]}})
                print(f"Content Profile {profile['_id']} updated successfully")
            except Exception as e:
                print(f"Error updating Content Profile {profile['_id']}: {str(e)}")

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
