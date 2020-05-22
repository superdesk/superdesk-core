# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : petr
# Creation: 2019-09-24 10:49

from superdesk.commands.data_updates import DataUpdate


class DataUpdate(DataUpdate):

    resource = "roles"
    privileges = [
        "publisher_dashboard",
        "planning_assignments_view",
        "monitoring_view",
        "spike_read",
        "highlights_read",
        "use_global_saved_searches",
        "dashboard",
        "ansa_metasearch",
        "ansa_live_assistant",
        "ansa_ai_news",
    ]

    def forwards(self, mongodb_collection, mongodb_database):
        updates = {}
        for privilege in self.privileges:
            updates["privileges.{}".format(privilege)] = 1

        result = mongodb_collection.update_many({}, {"$set": updates})
        print("updated {}/{} roles".format(result.modified_count, result.matched_count))

    def backwards(self, mongodb_collection, mongodb_database):
        pass
