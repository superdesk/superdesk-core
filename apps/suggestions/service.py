# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from inspect import isawaitable

from eve.utils import ParsedRequest
import json
from quart_babel import gettext as _

from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.eve_async import AsyncBaseService, ElasticAsyncEveCursor


class SuggestionsService(AsyncBaseService):
    """Service used for live suggestions functionality."""

    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource, backend)
        self.provider = None

    async def get_async(self, req, lookup):
        """
        Return a list of items related to the given item. The given item id is retrieved
        from the lookup dictionary as 'item_id'
        """
        if "item_id" not in lookup:
            raise SuperdeskApiError.badRequestError(_("The item identifier is required"))
        item = await get_resource_service("archive_autosave").find_one_async(req=None, _id=lookup["item_id"])
        if not item:
            item = await get_resource_service("archive").find_one_async(req=None, _id=lookup["item_id"])
            if not item:
                raise SuperdeskApiError.notFoundError(_("Invalid item identifer"))

        keywords = self.provider.get_keywords(self._transform(item))
        if isawaitable(keywords):
            keywords = await keywords

        if not keywords:
            return ElasticAsyncEveCursor()

        query = {
            "query": {"filtered": {"query": {"query_string": {"query": " ".join(kwd["text"] for kwd in keywords)}}}}
        }

        req = ParsedRequest()
        req.args = {"source": json.dumps(query), "repo": "archive,published,archived"}

        return await get_resource_service("search").get_async(req=req, lookup=None)

    def _transform(self, item):
        """
        Transforms an item in dictionary form to plain text.
        :param item: dict
        :return: str
        """
        fields = ["slugline", "headline", "body_html", "body_text", "description_text"]
        return "\n\n".join(item[field] for field in fields if field in item)
