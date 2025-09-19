# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2025-09-18 14:03

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):
    resource = "users"

    def forwards(self, mongodb_collection, mongodb_database):
        # Iterate over all users with a monitoring:view preference
        for user in mongodb_collection.find({"user_preferences.monitoring:view": {"$exists": True}}):
            prefs = user.get("user_preferences", {})
            monitoring = prefs.get("monitoring:view", None)
            if isinstance(monitoring, dict):
                changed = False
                # Remove the specified keys if they exist
                for key in ["allowed", "category"]:
                    if key in monitoring:
                        monitoring.pop(key)
                        changed = True
                if changed:
                    prefs["monitoring:view"] = monitoring
                    mongodb_collection.update_one({"_id": user["_id"]}, {"$set": {"user_preferences": prefs}})

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
