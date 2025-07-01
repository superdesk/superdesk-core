# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import bson

import superdesk
from superdesk.eve_async import AsyncBaseService
from superdesk.utils import format_content_type_name


class ContentTypesService(AsyncBaseService):
    async def get_output_name(self, profile):
        try:
            _id = bson.ObjectId(profile)
            item = (await superdesk.get_resource_service("content_types").find_one_async(req=None, _id=_id)) or {}
            return format_content_type_name(item, str(_id))
        except bson.errors.InvalidId:
            return "None"
