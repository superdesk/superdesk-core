# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from superdesk.resource import Resource
from superdesk.eve_async import AsyncBaseService
from superdesk.errors import SuperdeskApiError
from quart_babel import gettext as _

logger = logging.getLogger(__name__)


class RuleSetsResource(Resource):
    schema = {
        "name": {
            "type": "string",
            "iunique": True,
            "required": True,
            "nullable": False,
            "empty": False,
            "minlength": 1,
        },
        "rules": {"type": "list"},
    }

    privileges = {"POST": "rule_sets", "DELETE": "rule_sets", "PATCH": "rule_sets"}

    mongo_indexes = {
        "name_1": ([("name", 1)], {"unique": True}),
    }


class RuleSetsService(AsyncBaseService):
    async def update_async(self, id, updates, original):
        """
        Overriding to set the value of "new" attribute of rules to empty string if it's None.
        """

        for rule in updates.get("rules", {}):
            if rule["new"] is None:
                rule["new"] = ""

        return await super().update_async(id, updates, original)

    async def on_delete_async(self, doc):
        if await self.backend.find_one_async("ingest_providers", req=None, rule_set=doc["_id"]):
            raise SuperdeskApiError.forbiddenError(_("Cannot delete Rule set as it's associated with channel(s)."))
