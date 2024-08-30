import os
import shutil
import tempfile
from unittest.mock import patch

from superdesk.core import json
from apps.prepopulate.app_initialize import app_initialize_data_handler
from apps.prepopulate.app_scaffold_data import AppScaffoldDataCommand
from apps.prepopulate.app_initialize import fillEnvironmentVariables
from superdesk import get_resource_service
from superdesk.tests import TestCase


class AppInitializeWithDataCommandTestCase(TestCase):
    async def _run(self, *a, **kw):
        command = app_initialize_data_handler
        return await command(*a, **kw)

    async def test_app_initialization(self):
        result = await self._run()
        self.assertEqual(result, 0)

    async def test_app_initialization_multiple_loads(self):
        result = await self._run()
        self.assertEqual(result, 0)
        result = await self._run()
        self.assertEqual(result, 0)

    async def test_data_scaffolding(self):
        result = await self._run(["desks", "stages"], sample_data=True)
        self.assertEqual(result, 0)

        docs = [
            {
                "_id": str(x),
                "type": "text",
                "abstract": "test abstract {}".format(x),
                "headline": "test headline {}".format(x),
                "body_html": "test long story body {}".format(x),
                "state": "published",
            }
            for x in range(0, 40)
        ]
        get_resource_service("published").post(docs)

        stories_per_desk = 2
        existing_desks = 18
        command = AppScaffoldDataCommand()
        result = command.run(stories_per_desk)
        self.assertEqual(result, 0)

        cursor = get_resource_service("desks").get_from_mongo(None, {})
        self.assertEqual(cursor.count(), existing_desks)

        cursor = get_resource_service("archive").get_from_mongo(None, {})
        self.assertEqual(cursor.count(), existing_desks * stories_per_desk)

    async def test_sample_data(self):
        result = await self._run(sample_data=True)
        self.assertEqual(result, 0)

        cursor = get_resource_service("desks").get_from_mongo(None, {})
        self.assertEqual(cursor.count(), 18)

    async def test_app_initialization_index_creation(self):
        result = await self._run()
        self.assertEqual(result, 0)
        result = self.app.data.mongo.pymongo(resource="archive").db["archive"].index_information()
        self.assertTrue("groups.refs.residRef_1" in result)
        self.assertTrue(result["groups.refs.residRef_1"]["sparse"])

    @patch.dict(os.environ, {"REUTERS_USERNAME": "r_u", "REUTERS_PASSWORD": "r_p"})
    async def test_app_initialization_set_env_variables(self):
        item = {"username": "#ENV_REUTERS_USERNAME#", "password": "#ENV_REUTERS_PASSWORD#"}
        crt_item = fillEnvironmentVariables(item)
        self.assertEqual(crt_item["username"], "r_u")
        self.assertEqual(crt_item["password"], "r_p")

    @patch.dict(os.environ, {"REUTERS_USERNAME": "", "REUTERS_PASSWORD": "r_p"})
    async def test_app_initialization_notset_env_variables(self):
        item = {"username": "#ENV_REUTERS_USERNAME#", "password": "#ENV_REUTERS_PASSWORD#"}
        crt_item = fillEnvironmentVariables(item)
        self.assertTrue(not crt_item)

    async def test_init_keeps_user_modifications(self):
        await self._run(["vocabularies"])
        urgency = self.app.data.find_one("vocabularies", req=None, _id="urgency")
        self.assertIsNotNone(urgency)
        self.assertEqual("init", urgency["_etag"])

        updates = {"display_name": "FOO"}
        self.app.data.update("vocabularies", "urgency", updates, urgency)

        await self._run(["vocabularies"])
        urgency = self.app.data.find_one("vocabularies", req=None, _id="urgency")
        self.assertEqual("FOO", urgency["display_name"])
        self.assertNotEqual("init", urgency["_etag"])

        await self._run(["vocabularies"], None, None, True)
        urgency = self.app.data.find_one("vocabularies", req=None, _id="urgency")
        self.assertEqual("Urgency", urgency["display_name"])
        self.assertEqual("init", urgency["_etag"])

    async def test_init_can_combine_files_from_folders(self):
        init_dir = tempfile.mkdtemp("init", "test")
        self.app.config.update({"INIT_DATA_PATH": init_dir})

        with open(os.path.join(init_dir, "vocabularies.json"), "w") as f:
            f.write(json.dumps([{"_id": "foo"}]))
            f.flush()

        await self._run(["vocabularies"])
        self.assertEqual(self.app.data.find("vocabularies", req=None, lookup={})[0].count(), 1)

        await self._run(["validators"])
        self.assertGreater(self.app.data.find("validators", req=None, lookup={})[0].count(), 0)

        self.app.config.pop("INIT_DATA_PATH", None)
        shutil.rmtree(init_dir)
