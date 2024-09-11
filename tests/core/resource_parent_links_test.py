from superdesk.core.resources.resource_rest_endpoints import ResourceRestEndpoints
from superdesk.tests import AsyncFlaskTestCase

from .fixtures.users import john_doe, jane_doe


class ResourceParentLinksTestCase(AsyncFlaskTestCase):
    app_config = {
        "MODULES": [
            "tests.core.modules.users",
            "tests.core.modules.company",
            "tests.core.modules.topics",
        ]
    }

    async def test_parent_url_links(self):
        user_collection = self.async_app.mongo.get_collection_async("user_topic_folders")
        company_collection = self.async_app.mongo.get_collection_async("company_topic_folders")
        test_user1 = john_doe()
        test_user2 = jane_doe()

        # First add the 2 users we'll use for filtering/testing
        response = await self.test_client.post("/api/users_async", json=[test_user1, test_user2])
        self.assertEqual(response.status_code, 201)

        # Make sure the folders resource is empty
        self.assertEqual(await user_collection.count_documents({}), 0)
        response = await self.test_client.get(f"/api/users_async/{test_user1.id}/topic_folders")
        self.assertEqual(len((await response.get_json())["_items"]), 0)

        # Add a folder for each user
        response = await self.test_client.post(
            f"/api/users_async/{test_user1.id}/topic_folders", json=dict(name="Sports", section="wire")
        )
        self.assertEqual(response.status_code, 201)
        response = await self.test_client.post(
            f"/api/users_async/{test_user2.id}/topic_folders", json=dict(name="Finance", section="agenda")
        )
        self.assertEqual(response.status_code, 201)

        # Make sure all folders exist in the mongo collection
        self.assertEqual(await user_collection.count_documents({}), 2)
        # points to same collection as users folders, so it too should have 2 documents
        self.assertEqual(await company_collection.count_documents({}), 2)

        # Test getting folders for User1
        response = await self.test_client.get(f"/api/users_async/{test_user1.id}/topic_folders")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(len(data["_items"]), 1)
        self.assertEqual(data["_meta"]["total"], 1)
        self.assertDictContains(data["_items"][0], dict(user=test_user1.id, name="Sports", section="wire"))

        # Test getting folders for User2
        response = await self.test_client.get(f"/api/users_async/{test_user2.id}/topic_folders")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(len(data["_items"]), 1)
        self.assertEqual(data["_meta"]["total"], 1)
        self.assertDictContains(data["_items"][0], dict(user=test_user2.id, name="Finance", section="agenda"))

        # Test searching folders for User1
        user1_folders_url = f"/api/users_async/{test_user1.id}/topic_folders"
        response = await self.test_client.post(user1_folders_url, json=dict(name="Finance", section="agenda"))
        self.assertEqual(response.status_code, 201)

        # Make sure there are 2 folders when not filtering
        response = await self.test_client.get(user1_folders_url)
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(len(data["_items"]), 2)

        # Make sure there is only 1 folder when filtering
        response = await self.test_client.get(user1_folders_url + '?where={"section":"wire"}')
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(len(data["_items"]), 1)
        self.assertEqual(data["_meta"]["total"], 1)
        self.assertDictContains(data["_items"][0], dict(user=test_user1.id, name="Sports", section="wire"))

    async def test_patch_and_delete(self):
        # Create the user
        test_user1 = john_doe()
        response = await self.test_client.post("/api/users_async", json=test_user1)
        self.assertEqual(response.status_code, 201)

        # Create the users folder
        response = await self.test_client.post(
            f"/api/users_async/{test_user1.id}/topic_folders", json=dict(name="Sports", section="wire")
        )
        self.assertEqual(response.status_code, 201)
        folder_id = (await response.get_json())[0]

        # Get the folder, so we can use it's etag
        response = await self.test_client.get(f"/api/users_async/{test_user1.id}/topic_folders/{folder_id}")
        folder = await response.get_json()

        # Update the users folder
        response = await self.test_client.patch(
            f"/api/users_async/{test_user1.id}/topic_folders/{folder_id}",
            json=dict(name="Swimming"),
            headers={"If-Match": folder["_etag"]},
        )
        self.assertEqual(response.status_code, 200)

        # Delete the users folder
        response = await self.test_client.get(f"/api/users_async/{test_user1.id}/topic_folders/{folder_id}")
        folder = await response.get_json()
        response = await self.test_client.delete(
            f"/api/users_async/{test_user1.id}/topic_folders/{folder_id}", headers={"If-Match": folder["_etag"]}
        )
        self.assertEqual(response.status_code, 204)

    async def test_parent_link_validation(self):
        test_user1 = john_doe()

        # Test request returns 404 when parent item does not exist in the DB
        response = await self.test_client.post(
            f"/api/users_async/{test_user1.id}/topic_folders", json=dict(name="Sports", section="wire")
        )
        self.assertEqual(response.status_code, 404)

        # Now add the parent item, and test request returns 201
        response = await self.test_client.post("/api/users_async", json=test_user1)
        self.assertEqual(response.status_code, 201)
        response = await self.test_client.post(
            f"/api/users_async/{test_user1.id}/topic_folders", json=dict(name="Sports", section="wire")
        )
        self.assertEqual(response.status_code, 201)

    def test_generated_resource_url(self):
        config = self.async_app.resources.get_config("user_topic_folders")
        endpoint = ResourceRestEndpoints(config, config.rest_endpoints)
        self.assertEqual(endpoint.get_resource_url(), 'users_async/<regex("[\\w,.:_-]+"):user>/topic_folders')

        config = self.async_app.resources.get_config("company_topic_folders")
        endpoint = ResourceRestEndpoints(config, config.rest_endpoints)
        self.assertEqual(endpoint.get_resource_url(), 'companies/<regex("[\\w,.:_-]+"):company>/topic_folders')
