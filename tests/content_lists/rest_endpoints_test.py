# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from bson import ObjectId

from superdesk.tests import TestCase
from superdesk.default_settings import DATE_FORMAT
from superdesk.core.auth.user_auth import UserAuthProtocol
from superdesk.core.types import Request

from apps.content_lists.service import ContentListsService, ContentListItemsService, DUPLICATE_ITEMS_ERROR


class StubUserAuth(UserAuthProtocol):
    """Authenticates every request as a fixed user without a real session."""

    def __init__(self, user):
        self.user = user

    async def authenticate(self, request: Request):
        await self.continue_session(request, self.user)

    def get_current_user(self, request: Request):
        return self.user


ADMIN_USER = {"_id": "test-admin", "user_type": "administrator"}
PLAIN_USER = {"_id": "test-user", "user_type": "user", "privileges": {}}


class ContentListsRestTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._original_auth = self.async_app.auth
        self.async_app.auth = StubUserAuth(ADMIN_USER)
        self.addCleanup(self._restore_auth)
        self.lists_service = ContentListsService()
        self.items_service = ContentListItemsService()

    def _restore_auth(self):
        self.async_app.auth = self._original_auth

    async def _seed_archive(self, *item_ids):
        collection = self.async_app.mongo.get_collection_async("archive")
        await collection.insert_many([{"_id": item_id, "guid": item_id, "type": "text"} for item_id in item_ids])

    async def _create_list(self, name="Test list"):
        return (await self.lists_service.create([{"name": name, "type": "manual"}]))[0]

    async def _add_item(self, list_id, content, position=0):
        data = {
            "items": [{"action": "add", "contentId": content, "position": position}],
            "updatedAt": "initial",
        }
        content_list = await self.lists_service.find_by_id(list_id)
        if content_list.content_list_items_updated_at is not None:
            data["updatedAt"] = content_list.content_list_items_updated_at.strftime(DATE_FORMAT)
        await self.items_service.bulk_patch(list_id, data)

    async def test_create_and_get_list(self):
        response = await self.test_client.post(
            "/api/content_lists", json={"name": "Homepage", "type": "manual", "description": "Front page"}
        )
        self.assertEqual(response.status_code, 201)
        list_id = (await response.get_json())["_id"]

        response = await self.test_client.get(f"/api/content_lists/{list_id}")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["name"], "Homepage")
        self.assertEqual(data["type"], "manual")
        self.assertTrue(data["enabled"])

    async def test_unauthenticated_request_is_rejected(self):
        self.async_app.auth = self._original_auth
        response = await self.test_client.get("/api/content_lists")
        self.assertEqual(response.status_code, 401)

    async def test_nested_items_route_is_scoped_to_parent_list(self):
        await self._seed_archive("article-1", "article-2")
        list_one = await self._create_list("List one")
        list_two = await self._create_list("List two")
        await self._add_item(list_one.id, "article-1")
        await self._add_item(list_two.id, "article-2")

        response = await self.test_client.get(f"/api/content_lists/{list_one.id}/items")
        self.assertEqual(response.status_code, 200)
        items = (await response.get_json())["_items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"], "article-1")

    async def test_bulk_patch_endpoint_success(self):
        await self._seed_archive("article-1")
        content_list = await self._create_list()

        response = await self.test_client.patch(
            f"/api/content_lists/{content_list.id}/items",
            json={
                "items": [{"action": "add", "contentId": "article-1", "position": 0}],
                "updatedAt": "initial",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertIsNotNone(data["content_list_items_updated_at"])

        items = (await (await self.test_client.get(f"/api/content_lists/{content_list.id}/items")).get_json())["_items"]
        self.assertEqual(items[0]["content"], "article-1")
        self.assertEqual(items[0]["position"], 0)

    async def test_bulk_patch_endpoint_error_statuses(self):
        content_list = await self._create_list()
        url = f"/api/content_lists/{content_list.id}/items"

        response = await self.test_client.patch(url, json={"updatedAt": "x"})
        self.assertEqual(response.status_code, 400)

        response = await self.test_client.patch(
            f"/api/content_lists/{ObjectId()}/items", json={"items": [], "updatedAt": "x"}
        )
        self.assertEqual(response.status_code, 404)

        response = await self.test_client.patch(url, json={"items": [], "updatedAt": "first"})
        self.assertEqual(response.status_code, 200)
        response = await self.test_client.patch(url, json={"items": [], "updatedAt": "stale"})
        self.assertEqual(response.status_code, 409)

    async def test_bulk_patch_duplicate_item_returns_message(self):
        await self._seed_archive("article-1")
        content_list = await self._create_list()
        await self._add_item(content_list.id, "article-1")
        content_list = await self.lists_service.find_by_id(content_list.id)

        response = await self.test_client.patch(
            f"/api/content_lists/{content_list.id}/items",
            json={
                "items": [{"action": "add", "contentId": "article-1", "position": 1}],
                "updatedAt": content_list.content_list_items_updated_at.strftime(DATE_FORMAT),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual((await response.get_json())["_message"], DUPLICATE_ITEMS_ERROR)

    async def test_items_response_includes_article_content(self):
        collection = self.async_app.mongo.get_collection_async("archive")
        await collection.insert_one(
            {"_id": "article-1", "guid": "article-1", "type": "text", "headline": "Hello", "state": "published"}
        )
        content_list = await self._create_list()
        await self._add_item(content_list.id, "article-1")
        # An item pointing at a missing article, inserted directly to bypass
        # the archive relation validation.
        items_collection = self.async_app.mongo.get_collection_async("content_list_items")
        await items_collection.insert_one(
            {"_id": ObjectId(), "list_id": content_list.id, "content": "ghost", "position": 1}
        )

        response = await self.test_client.get(f"/api/content_lists/{content_list.id}/items")
        self.assertEqual(response.status_code, 200)
        items = {item["content"]: item for item in (await response.get_json())["_items"]}
        self.assertEqual(items["article-1"]["article_content"]["title"], "Hello")
        self.assertEqual(items["article-1"]["article_content"]["state"], "published")
        self.assertIsNone(items["ghost"]["article_content"])

        item_id = items["article-1"]["_id"]
        response = await self.test_client.get(f"/api/content_lists/{content_list.id}/items/{item_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await response.get_json())["article_content"]["title"], "Hello")

    async def test_patch_list_ignores_server_managed_timestamp(self):
        content_list = await self._create_list()
        etag = await self.get_resource_etag("content_lists", str(content_list.id))

        response = await self.test_client.patch(
            f"/api/content_lists/{content_list.id}",
            json={"description": "updated", "content_list_items_updated_at": "2020-01-01T00:00:00+0000"},
            headers={"If-Match": etag},
        )
        self.assertEqual(response.status_code, 200)

        data = await (await self.test_client.get(f"/api/content_lists/{content_list.id}")).get_json()
        self.assertEqual(data["description"], "updated")
        self.assertIsNone(data.get("content_list_items_updated_at"))

    async def test_webhooks_resource_requires_privilege(self):
        response = await self.test_client.post("/api/content_list_webhooks", json={"url": "https://example.com/hook"})
        self.assertEqual(response.status_code, 201)
        webhook_id = (await response.get_json())["_id"]
        response = await self.test_client.get("/api/content_list_webhooks")
        self.assertEqual(response.status_code, 200)

        self.async_app.auth = StubUserAuth(PLAIN_USER)
        webhook_url = f"/api/content_list_webhooks/{webhook_id}"
        response = await self.test_client.get("/api/content_list_webhooks")
        self.assertEqual(response.status_code, 403)
        response = await self.test_client.post("/api/content_list_webhooks", json={"url": "https://other.example.com/"})
        self.assertEqual(response.status_code, 403)
        response = await self.test_client.patch(webhook_url, json={"enabled": False})
        self.assertEqual(response.status_code, 403)
        response = await self.test_client.delete(webhook_url)
        self.assertEqual(response.status_code, 403)
