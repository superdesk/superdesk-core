# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from ..service import ProdApiService
import bson
import re
import superdesk


class ContentTypesService(ProdApiService):
    excluded_fields = ProdApiService.excluded_fields

    def get_output_name(self, profile):
        try:
            _id = bson.ObjectId(profile)
            item = superdesk.get_resource_service("content_types").find_one(req=None, _id=_id) or {}
            name = item.get("output_name") or item.get("label", str(_id))
            return re.compile("[^0-9a-zA-Z_]").sub("", name)
        except bson.errors.InvalidId:
            return profile
