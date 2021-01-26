# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : superdesk
# Creation: 2017-02-14 14:53

from superdesk.commands.data_updates import BaseDataUpdate
from superdesk import get_resource_service


class DataUpdate(BaseDataUpdate):

    resource = "vocabularies"
    product_types = {
        "_id": "product_types",
        "display_name": "Product Types",
        "type": "unmanageable",
        "items": [
            {"is_active": True, "name": "API", "qcode": "api"},
            {"is_active": True, "name": "Direct", "qcode": "direct"},
            {"is_active": True, "name": "Both", "qcode": "both"},
        ],
    }

    def forwards(self, mongodb_collection, mongodb_database):
        product_types = get_resource_service(self.resource).find_one(req=None, _id="product_types")
        if product_types:
            print("Product Types vocabulary already exists in the system.")
            return
        get_resource_service(self.resource).post([self.product_types])

    def backwards(self, mongodb_collection, mongodb_database):
        get_resource_service(self.resource).delete_action({"_id": "product_types"})
