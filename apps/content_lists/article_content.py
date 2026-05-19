from typing import Any

import superdesk
from superdesk.core.types import RestGetResponse
from superdesk.etree import parse_html


async def attach_article_content(items: list[dict[str, Any]]) -> None:
    """Add an ``article_content`` summary to each content list item in place."""
    article_ids = [item["content"] for item in items if item.get("content")]
    if not article_ids:
        for item in items:
            item["article_content"] = None
        return

    archive_service = superdesk.get_resource_service("archive")
    cursor = await archive_service.get_from_mongo_async(
        req=None,
        lookup={"_id": {"$in": article_ids}},
        projection={"headline": 1, "state": 1, "associations": 1, "body_html": 1},
    )
    articles_by_id: dict[str, dict[str, Any]] = {}
    async for article in cursor:
        articles_by_id[article["_id"]] = article

    for item in items:
        article = articles_by_id.get(item.get("content"))
        item["article_content"] = _build_article_content(article) if article else None


def _build_article_content(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": article.get("headline"),
        "state": article.get("state"),
        "thumbnail": _get_thumbnail(article),
    }


def _get_thumbnail(article: dict[str, Any]) -> dict[str, Any] | str | None:
    feature_media = (article.get("associations") or {}).get("featuremedia") or {}
    thumbnail = (feature_media.get("renditions") or {}).get("thumbnail")
    if thumbnail:
        return thumbnail

    body_html = article.get("body_html")
    if body_html:
        return _first_body_html_image(body_html)

    return None


def _first_body_html_image(body_html: str) -> str | None:
    try:
        root = parse_html(body_html, content="html")
    except Exception:
        return None
    img = root.find(".//img")
    if img is None:
        return None
    src = img.get("src")
    return src or None


async def enrich_fetched_response(doc: RestGetResponse) -> None:
    """Hook for ``on_fetched``: enriches all items in a search response."""
    await attach_article_content(doc.get("_items") or [])


async def enrich_fetched_item(item: dict[str, Any]) -> None:
    """Hook for ``on_fetched_item``: enriches a single item."""
    await attach_article_content([item])
