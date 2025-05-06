import json
from typing import Any, List, Union

import apps.archive  # NOQA

# XXX: This import is needed in order to avoid ImportError when importing
# package_service, caused by circular dependencies.
# When that issue is resolved, the workaround should be removed.

from superdesk.core import get_current_app, get_app_config
import apps.packages.package_service as package
from superdesk import get_resource_service
from superdesk.eve_async import AsyncBaseService
from eve.utils import ParsedRequest
from superdesk.notification import push_notification
from superdesk.utc import get_timezone_offset, utcnow
from apps.archive.common import ITEM_MARK, ITEM_UNMARK
from bson import ObjectId


def init_parsed_request(elastic_query):
    parsed_request = ParsedRequest()
    parsed_request.args = {"source": json.dumps(elastic_query)}
    return parsed_request


async def get_highlighted_items(highlights_id):
    """Get items marked for given highlight and passing date range query."""
    highlight = await get_resource_service("highlights").find_one_async(req=None, _id=highlights_id)
    query = {
        "query": {
            "filtered": {
                "filter": {
                    "and": [
                        {
                            "range": {
                                "versioncreated": {
                                    "gte": highlight.get("auto_insert", "now/d"),
                                    "time_zone": get_timezone_offset(get_app_config("DEFAULT_TIMEZONE"), utcnow()),
                                }
                            }
                        },
                        {"term": {"highlights": str(highlights_id)}},
                    ]
                }
            }
        },
        "sort": [
            {"versioncreated": "desc"},
        ],
        "size": 200,
    }
    request = ParsedRequest()
    request.args = {"source": json.dumps(query), "repo": "archive,published"}
    return await get_resource_service("search").get_async(req=request, lookup=None)


async def init_highlight_package(doc):
    """Add to package items marked for doc highlight."""
    main_group = doc.get("groups")[1]
    items = await get_highlighted_items(doc.get("highlight"))
    used_items = []
    async for item in items:
        if item["_id"] not in used_items:
            main_group["refs"].append(package.get_item_ref(item))
            used_items.append(item["_id"])


async def init_default_content_profile(doc):
    if not doc.get("profile"):
        desk_id = doc.get("task", {}).get("desk")
        desk = await get_resource_service("desks").find_one_async(req=None, _id=desk_id)
        doc["profile"] = desk.get("default_content_profile")


async def on_create_package(docs: list[dict]) -> None:
    """Call init_highlight_package for each package with highlight reference."""
    for doc in docs:
        if doc.get("highlight"):
            await init_highlight_package(doc)
            await init_default_content_profile(doc)


async def get_highlight_name(highlights_id):
    """
    Given the id of a highlight it will return the name.
    :param hightlight_id:
    :return:
    """
    highlight = await get_resource_service("highlights").find_one_async(req=None, _id=highlights_id)
    if highlight and "name" in highlight:
        return highlight.get("name", None)
    return None


class HighlightsService(AsyncBaseService):
    async def on_delete_async(self, doc):
        service = get_resource_service("archive")
        highlights_id = str(doc["_id"])
        query = {"query": {"filtered": {"filter": {"term": {"highlights": highlights_id}}}}}
        req = init_parsed_request(query)
        proposed_items = await service.get_async(req=req, lookup=None)
        app = get_current_app().as_any()
        async for item in proposed_items:
            await app.on_archive_item_updated.call_async(
                {"highlight_id": highlights_id, "highlight_name": await get_highlight_name(highlights_id)},
                item,
                ITEM_UNMARK,
            )
            highlights = [h for h in item.get("highlights") if h != highlights_id]
            await service.update_async(item["_id"], {"highlights": highlights}, item)


class MarkedForHighlightsService(AsyncBaseService):
    async def create_async(self, docs, **kwargs):
        """Toggle highlight status for given highlight and item."""
        service = get_resource_service("archive")
        published_service = get_resource_service("published")
        ids = []
        app = get_current_app().as_any()
        for doc in docs:
            item = await service.find_one_async(req=None, _id=doc["marked_item"])
            if not item:
                ids.append(None)
                continue
            ids.append(item["_id"])
            highlights = item.get("highlights") or []

            doc_highlights: List[Union[ObjectId, str]] = doc["highlights"] or []
            if doc_highlights and not isinstance(doc_highlights, list):
                doc_highlights = [doc_highlights]
            status = {}
            for highlight in doc_highlights:
                if highlight not in highlights:
                    highlights.append(highlight)
                    status[str(highlight)] = ITEM_MARK
                else:
                    highlights = [h for h in highlights if h != highlight]
                    status[str(highlight)] = ITEM_UNMARK

            updates = {"highlights": highlights, "_etag": item["_etag"]}
            await service.update_async(item["_id"], updates, item)

            published_items = await published_service.find_async({"item_id": item["_id"]})
            async for published_item in published_items:
                if published_item["_current_version"] == item["_current_version"]:
                    updates = {
                        "highlights": highlights,
                        "_updated": published_item["_updated"],
                        "_etag": published_item["_etag"],
                    }
                    await published_service.update_async(published_item["_id"], updates, published_item)

            for highlight in doc_highlights:
                await app.on_archive_item_updated.call_async(
                    {"highlight_id": highlight, "highlight_name": await get_highlight_name(highlight)},
                    item,
                    status[str(highlight)],
                )

                push_notification(
                    "item:highlights",
                    marked=int(status[str(highlight)] == ITEM_MARK),
                    item_id=item["_id"],
                    mark_id=str(highlight),
                )

        return ids


package.package_create_signal.connect(on_create_package)
