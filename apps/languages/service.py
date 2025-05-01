# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.types.vocabularies import CVItem
from superdesk.eve_async import AsyncBaseService, AsyncListCursor
from superdesk.vocabularies_async import get_languages


def view_language(item: CVItem) -> dict:
    language = item.to_dict()
    language["_id"] = language["qcode"]
    language["label"] = language["name"]
    language["language"] = language["qcode"]

    # allow translations
    language.setdefault("source", True)
    language.setdefault("destination", True)

    return language


class LanguagesService(AsyncBaseService):
    async def get_async(self, req, lookup):
        """
        Return the list of languages defined on config file.
        """
        languages = await get_languages()
        return AsyncListCursor([view_language(lang) for lang in languages])
