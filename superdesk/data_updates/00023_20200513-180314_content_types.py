# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : GyanP
# Creation: 2020-05-13 18:03

from copy import deepcopy
from superdesk.commands.data_updates import BaseDataUpdate
from eve.utils import config


class DataUpdate(BaseDataUpdate):

    resource = "content_types"

    def forwards(self, mongodb_collection, mongodb_database):
        for content_type in mongodb_collection.find({}):
            if "schema" not in content_type:
                continue
            original_schema = deepcopy(content_type["schema"])
            for field, description in content_type["schema"].items():
                if description and description.get("mandatory_in_list"):
                    custom_fields = description.get("mandatory_in_list").get("scheme")
                    if custom_fields is not None:
                        for custom_field, custom_value in custom_fields.items():
                            # old notation
                            if custom_field == custom_value:
                                custom_fields[custom_field] = {
                                    "required": True,
                                    "readonly": False,
                                }
                            # new notation
                            elif type(custom_value) is dict:
                                custom_fields[custom_field] = {
                                    "required": custom_value.get("required", False),
                                    "readonly": custom_value.get("readonly", False),
                                }
                            # default
                            else:
                                custom_fields[custom_field] = {
                                    "required": False,
                                    "readonly": False,
                                }

            if original_schema != content_type["schema"]:
                print("update schema in content type", content_type["label"])
                mongodb_collection.update(
                    {"_id": content_type.get(config.ID_FIELD)}, {"$set": {"schema": content_type["schema"]}}
                )

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
