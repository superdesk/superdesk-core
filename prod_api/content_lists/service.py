# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId

from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from apps.content_lists.article_content import attach_article_content

from ..service import ProdApiService


ENABLED_PARAM = "enabled"
ENABLED_VALUES = ("true", "false", "all")


def apply_enabled_filter(req, lookup: dict) -> None:
    """Apply the ``enabled`` query parameter to a mongo lookup.

    Only enabled documents are returned by default. ``?enabled=false`` returns
    disabled documents only and ``?enabled=all`` disables the filter.
    """
    value = (req.args.get(ENABLED_PARAM) if req is not None and req.args else None) or "true"
    if value == "all":
        return
    if value == "true":
        # documents without the key count as enabled
        lookup[ENABLED_PARAM] = {"$ne": False}
    elif value == "false":
        lookup[ENABLED_PARAM] = False
    else:
        raise SuperdeskApiError.badRequestError(
            "Invalid value for '{}', must be one of: {}".format(ENABLED_PARAM, ", ".join(ENABLED_VALUES))
        )


class ContentListsService(ProdApiService):
    excluded_fields = {
        "filters",
        "cache_life_time",
    } | ProdApiService.excluded_fields

    async def get_async(self, req, lookup):
        lookup = dict(lookup or {})
        apply_enabled_filter(req, lookup)
        return await super().get_async(req, lookup)

    def _process_fetched_object(self, doc):
        super()._process_fetched_object(doc)
        doc.setdefault("_links", {})["items"] = {
            "title": "Items",
            "href": "content_lists/{}/items".format(doc["_id"]),
        }


class ContentListItemsService(ProdApiService):
    # there is no item endpoint, and eve would render the raw sub-resource
    # url regex into the self link
    excluded_fields = {"_links"} | ProdApiService.excluded_fields

    async def get_async(self, req, lookup):
        lookup = dict(lookup or {})
        list_id = ObjectId(lookup.pop("list_id"))
        content_list = await get_resource_service("content_lists").find_one_async(req=None, _id=list_id)
        if not content_list:
            # disabled lists are served too, only unknown ids are an error
            raise SuperdeskApiError.notFoundError("Content list {} not found".format(list_id))
        lookup["list_id"] = list_id
        apply_enabled_filter(req, lookup)
        return await super().get_async(req, lookup)

    async def on_fetched_async(self, result):
        await super().on_fetched_async(result)
        await attach_article_content(result["_items"])
        for item in result["_items"]:
            thumbnail = (item.get("article_content") or {}).get("thumbnail")
            if isinstance(thumbnail, dict):
                # rewrite the rendition href to point at the production api assets url
                self._process_item_renditions({"renditions": {"thumbnail": thumbnail}})
