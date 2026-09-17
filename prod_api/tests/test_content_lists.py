import json

import bson

from superdesk.flask import url_for
from superdesk import get_resource_service

FRONT_PAGE_ID = "66f0000000000000000000a1"
DISABLED_LIST_ID = "66f0000000000000000000a3"

EXCLUDED_FIELDS = {"_etag", "_type", "_updated", "_created", "_current_version"}


async def _get_json(client, url):
    resp = await client.get(url)
    return resp, json.loads((await resp.get_data()).decode("utf-8"))


async def test_service_get(prodapi_app_with_data):
    """Both services read the content lists collections."""
    async with prodapi_app_with_data.app_context():
        lists_service = get_resource_service("content_lists")
        assert len(list(lists_service.get(req=None, lookup={}))) == 3

        items_service = get_resource_service("content_list_items")
        assert len(list(items_service.get(req=None, lookup={}))) == 5


async def test_readonly(prodapi_app_with_data, prodapi_app_with_data_client):
    """Both endpoints only allow GET."""
    async with prodapi_app_with_data.test_request_context("/"):
        for url in (
            url_for("content_lists|resource"),
            url_for("content_list_items|resource", list_id=FRONT_PAGE_ID),
        ):
            for method, status in (("get", 200), ("post", 405), ("patch", 405), ("put", 405), ("delete", 405)):
                resp = await getattr(prodapi_app_with_data_client, method)(url)
                assert resp.status_code == status, (method, url)

        # no item endpoints (eve keeps the route but allows no method on it)
        resp = await prodapi_app_with_data_client.get("/prodapi/v1/content_lists/{}".format(FRONT_PAGE_ID))
        assert resp.status_code == 405


async def test_lists_default_and_excluded_fields(prodapi_app_with_data, prodapi_app_with_data_client):
    """Only enabled lists by default, sorted by name, without internal fields."""
    async with prodapi_app_with_data.test_request_context("/"):
        resp, data = await _get_json(prodapi_app_with_data_client, url_for("content_lists|resource"))
        assert resp.status_code == 200
        assert [item["name"] for item in data["_items"]] == ["Front page", "Sports"]

        front_page = data["_items"][0]
        assert front_page["_id"] == FRONT_PAGE_ID
        assert front_page["type"] == "manual"
        assert front_page["limit"] == 10
        assert front_page["content_list_items_updated_at"]
        assert front_page["_links"]["items"] == {
            "title": "Items",
            "href": "content_lists/{}/items".format(FRONT_PAGE_ID),
        }
        for item in data["_items"]:
            assert not (set(item.keys()) & (EXCLUDED_FIELDS | {"filters", "cache_life_time"}))

        # eve `where` filtering still works
        resp, data = await _get_json(
            prodapi_app_with_data_client,
            url_for("content_lists|resource", where=json.dumps({"type": "bucket"})),
        )
        assert [item["name"] for item in data["_items"]] == ["Sports"]


async def test_lists_enabled_param(prodapi_app_with_data, prodapi_app_with_data_client):
    """The `enabled` query parameter overrides the default filter."""
    async with prodapi_app_with_data.test_request_context("/"):
        resp, data = await _get_json(prodapi_app_with_data_client, url_for("content_lists|resource", enabled="false"))
        assert resp.status_code == 200
        assert [item["_id"] for item in data["_items"]] == [DISABLED_LIST_ID]

        resp, data = await _get_json(prodapi_app_with_data_client, url_for("content_lists|resource", enabled="all"))
        assert len(data["_items"]) == 3

        resp, data = await _get_json(prodapi_app_with_data_client, url_for("content_lists|resource", enabled="true"))
        assert len(data["_items"]) == 2

        resp, data = await _get_json(prodapi_app_with_data_client, url_for("content_lists|resource", enabled="bogus"))
        assert resp.status_code == 400


async def test_items(prodapi_app_with_data, prodapi_app_with_data_client):
    """Items are sorted by position, enabled only by default and enriched with article content."""
    async with prodapi_app_with_data.test_request_context("/"):
        resp, data = await _get_json(
            prodapi_app_with_data_client, url_for("content_list_items|resource", list_id=FRONT_PAGE_ID)
        )
        assert resp.status_code == 200
        items = data["_items"]
        assert [item["position"] for item in items] == [0, 1, 2]
        assert all(item["list_id"] == FRONT_PAGE_ID for item in items)
        for item in items:
            assert not (set(item.keys()) & (EXCLUDED_FIELDS | {"_links"}))

        assert items[0]["sticky"] is True
        assert items[0]["article_content"]["title"] == "GDPR Headline"
        assert items[0]["article_content"]["state"]
        assert items[1]["article_content"] is None
        assert items[2]["article_content"]["title"] == "Dev one"

        # disabled item is included with enabled=all
        resp, data = await _get_json(
            prodapi_app_with_data_client,
            url_for("content_list_items|resource", list_id=FRONT_PAGE_ID, enabled="all"),
        )
        assert [item["position"] for item in data["_items"]] == [0, 1, 2, 3]

        resp, data = await _get_json(
            prodapi_app_with_data_client,
            url_for("content_list_items|resource", list_id=FRONT_PAGE_ID, enabled="false"),
        )
        assert [item["position"] for item in data["_items"]] == [3]


async def test_items_thumbnail_href(prodapi_app_with_data, prodapi_app_with_data_client):
    """Thumbnail renditions point at the production api assets url."""
    async with prodapi_app_with_data.app_context():
        prodapi_app_with_data.data.insert(
            "archive",
            [
                {
                    "_id": "urn:with-thumbnail",
                    "headline": "With picture",
                    "state": "published",
                    "associations": {
                        "featuremedia": {
                            "renditions": {
                                "thumbnail": {
                                    "href": "http://localhost:5000/api/upload-raw/5d553c343031e2855a2e5666.jpg",
                                    "media": "5d553c343031e2855a2e5666",
                                    "mimetype": "image/jpeg",
                                }
                            }
                        }
                    },
                }
            ],
        )
        prodapi_app_with_data.data.insert(
            "content_list_items",
            [
                {
                    "_id": bson.ObjectId(),
                    "list_id": bson.ObjectId("66f0000000000000000000a2"),
                    "content": "urn:with-thumbnail",
                    "position": 0,
                    "enabled": True,
                }
            ],
        )

    async with prodapi_app_with_data.test_request_context("/"):
        resp, data = await _get_json(
            prodapi_app_with_data_client,
            url_for("content_list_items|resource", list_id="66f0000000000000000000a2"),
        )
        assert resp.status_code == 200
        thumbnail = data["_items"][0]["article_content"]["thumbnail"]
        assert "media" not in thumbnail
        assert thumbnail["href"].startswith("http://localhost:5500/prodapi/v1/assets/")
        assert thumbnail["href"].endswith("5d553c343031e2855a2e5666.jpg")


async def test_items_of_disabled_list(prodapi_app_with_data, prodapi_app_with_data_client):
    """Items of a disabled list are served."""
    async with prodapi_app_with_data.test_request_context("/"):
        resp, data = await _get_json(
            prodapi_app_with_data_client, url_for("content_list_items|resource", list_id=DISABLED_LIST_ID)
        )
        assert resp.status_code == 200
        assert len(data["_items"]) == 1
        assert data["_items"][0]["article_content"]["title"] == "Mehr als 200 Migranten in der Ägäis aufgegriffen"


async def test_items_unknown_list(prodapi_app_with_data, prodapi_app_with_data_client):
    """Unknown list id is a 404."""
    async with prodapi_app_with_data.test_request_context("/"):
        resp = await prodapi_app_with_data_client.get(
            url_for("content_list_items|resource", list_id=str(bson.ObjectId()))
        )
        assert resp.status_code == 404
        # not a valid object id: no route
        resp = await prodapi_app_with_data_client.get("/prodapi/v1/content_lists/not-an-id/items")
        assert resp.status_code == 404
