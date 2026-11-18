# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : Helmy Giacoman
# Creation: 2026-11-18 12:55

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):
    """Move ``parameters.system_prompt`` of AI actions to ``parameters.extra_instructions``

    The meaning of a moved value changes: a ``system_prompt`` replaced the instructions built from
    the action type, ``extra_instructions`` is added after them. A prompt written to stand on its
    own may therefore repeat or contradict the built-in instructions and is worth reading again.

    An action that already holds ``extra_instructions`` keeps them and loses its ``system_prompt``:
    the extra instructions can only have been written after the rename, so they are the newer text.
    """

    resource = "ai_actions"
    use_async_resources = True

    async def forwards(self, mongodb_collection, mongodb_database):
        await mongodb_collection.update_many(
            {
                "parameters.system_prompt": {"$exists": True},
                "parameters.extra_instructions": {"$nin": [None, ""]},
            },
            {"$unset": {"parameters.system_prompt": ""}},
        )
        await mongodb_collection.update_many(
            {"parameters.system_prompt": {"$exists": True}},
            {"$rename": {"parameters.system_prompt": "parameters.extra_instructions"}},
        )

    async def backwards(self, mongodb_collection, mongodb_database):
        await mongodb_collection.update_many(
            {"parameters.extra_instructions": {"$exists": True}},
            {"$rename": {"parameters.extra_instructions": "parameters.system_prompt"}},
        )
