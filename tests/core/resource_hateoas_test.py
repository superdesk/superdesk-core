from superdesk.tests import AsyncFlaskTestCase
from tests.core.modules.module_related_resources import RingBearerService, RingOfPowerService, RingPowerService


class ResourceHateoasTestCase(AsyncFlaskTestCase):
    use_default_apps = True
    app_config = {
        "MODULES": [
            "tests.core.modules.module_related_resources",
        ]
    }

    async def create_registries(self):
        # create a ring bearer
        await RingBearerService().create([{"id": "bearer_1", "name": "Frodo Baggins"}])

        # create a ring power
        await RingPowerService().create([{"id": "power_1", "name": "Rule them all"}])

        # create a ring of power
        await RingOfPowerService().create(
            [
                {
                    "id": "the_one_ring",
                    "name": "The One Ring",
                    "bearer": "bearer_1",
                    "power": "power_1",
                }
            ]
        )

    async def test_hateoas_related_in_resources_items(self):
        """Checks hateoas is generated for a resource if configured to have hateoas"""
        await self.create_registries()

        response = await self.test_client.get("/api/ring_of_power")
        json_data = await response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("_items", json_data)
        self.assertIn("_links", json_data["_items"][0])

        links = json_data["_items"][0]["_links"]
        self.assertIn("related", links)

        # should contain two related items, one from parent class and one from child class
        self.assertEqual(len(links["related"]), 2)
        self.assertIn("bearer", links["related"])
        self.assertIn("power", links["related"])

    async def test_hateoas_related_in_single_item(self):
        """Checks hateoas is generated for a single item if configured to have hateoas"""
        await self.create_registries()

        response = await self.test_client.get("/api/ring_of_power/the_one_ring")
        json_data = await response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("_links", json_data)

        links = json_data["_links"]
        self.assertEqual(len(links["related"]), 2)
        self.assertIn("bearer", links["related"])
        self.assertIn("power", links["related"])

    async def test_hateoas_no_related_in_resources_items_no_hateoas(self):
        """Checks no hateoas is generated for a resource if configured to not have hateoas"""
        await self.create_registries()

        response = await self.test_client.get("/api/ring_of_power_no_hateoas")
        json_data = await response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("_links", json_data)
        self.assertNotIn("related", json_data["_links"])

    async def test_hateoas_no_related_in_single_item_no_hateoas(self):
        """Checks no hateoas is generated for a single item if the resource is configured to not have hateoas"""
        await self.create_registries()

        response = await self.test_client.get("/api/ring_of_power_no_hateoas/the_one_ring")
        json_data = await response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_links", json_data)
