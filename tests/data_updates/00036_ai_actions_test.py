import importlib

from bson import ObjectId

from superdesk.tests import TestCase

update_module = importlib.import_module("superdesk.data_updates.00036_20261118-125508_ai_actions")


class DataUpdate00036AIActionsTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.collection = self.async_app.mongo.get_collection_async("ai_actions")

    async def _insert(self, parameters):
        action_id = ObjectId()
        await self.collection.insert_one({"_id": action_id, "name": "Action", "parameters": parameters})
        return action_id

    async def _parameters(self, action_id):
        return (await self.collection.find_one({"_id": action_id}))["parameters"]

    async def test_forwards_moves_system_prompt_to_extra_instructions(self):
        action_id = await self._insert({"temperature": 0.2, "system_prompt": "Be brief"})

        await update_module.DataUpdate().apply("forwards")

        self.assertEqual(await self._parameters(action_id), {"temperature": 0.2, "extra_instructions": "Be brief"})

    async def test_forwards_keeps_extra_instructions_written_after_the_rename(self):
        action_id = await self._insert({"system_prompt": "Old prompt", "extra_instructions": "New text"})

        await update_module.DataUpdate().apply("forwards")

        self.assertEqual(await self._parameters(action_id), {"extra_instructions": "New text"})

    async def test_forwards_moves_system_prompt_over_empty_extra_instructions(self):
        """A parameters PATCH on an action stored before the rename stores the new key empty next to the old one"""

        for empty in (None, ""):
            with self.subTest(extra_instructions=empty):
                action_id = await self._insert({"system_prompt": "Old prompt", "extra_instructions": empty})

                await update_module.DataUpdate().apply("forwards")

                self.assertEqual(await self._parameters(action_id), {"extra_instructions": "Old prompt"})

    async def test_forwards_leaves_actions_without_system_prompt_alone(self):
        action_id = await self._insert({"temperature": 0.2})

        await update_module.DataUpdate().apply("forwards")

        self.assertEqual(await self._parameters(action_id), {"temperature": 0.2})

    async def test_backwards_moves_extra_instructions_back_to_system_prompt(self):
        action_id = await self._insert({"extra_instructions": "Be brief"})

        await update_module.DataUpdate().apply("backwards")

        self.assertEqual(await self._parameters(action_id), {"system_prompt": "Be brief"})
