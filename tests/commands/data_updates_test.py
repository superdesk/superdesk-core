import os
import shutil
from unittest import mock

import superdesk.commands.data_updates
from superdesk import get_resource_service
from superdesk.commands.data_updates import get_data_updates_files, GenerateUpdate, Upgrade, Downgrade, get_dirs
from superdesk.tests import TestCase

# change the folder where to store updates for test purpose
DEFAULT_DATA_UPDATE_DIR_NAME = "/tmp/data_updates"
MAIN_DATA_UPDATES_DIR = "/tmp/global_data_updates"


class DataUpdatesTestCase(TestCase):
    def setUp(self):

        dirs = (
            ("DEFAULT_DATA_UPDATE_DIR_NAME", "/tmp/data_updates"),
            ("MAIN_DATA_UPDATES_DIR", "/tmp/global_data_updates"),
        )
        for name, path in dirs:
            shutil.rmtree(path, True)
            os.mkdir(path)
            self.addCleanup(lambda path=path: shutil.rmtree(path))

            patcher = mock.patch("superdesk.commands.data_updates.%s" % name, path)
            self.addCleanup(patcher.stop)
            patcher.start()

        # update the default implementation for `forwards` and `backwards` function
        for n in ("FW", "BW"):
            name = "DEFAULT_DATA_UPDATE_%s_IMPLEMENTATION" % n
            patcher = mock.patch("superdesk.commands.data_updates.%s" % name, "pass")
            self.addCleanup(patcher.stop)
            patcher.start()

        self.app.config["APPS_DATA_UPDATES_PATHS"] = []

    def test_data_update_generation(self):
        assert len(get_data_updates_files()) == 0, get_data_updates_files()
        GenerateUpdate().run(resource_name="RESOURCE_NAME")
        assert len(get_data_updates_files()) == 1, get_data_updates_files()
        GenerateUpdate().run(resource_name="RESOURNCE_NAME")
        assert len(get_data_updates_files()) == 2, get_data_updates_files()

    def test_data_update_generation_create_updates_dir(self):
        updates_dir = DEFAULT_DATA_UPDATE_DIR_NAME
        shutil.rmtree(DEFAULT_DATA_UPDATE_DIR_NAME)
        self.assertFalse(os.path.exists(updates_dir))
        self.app.config["DATA_UPDATES_PATH"] = updates_dir
        GenerateUpdate().run("tmp")
        self.assertTrue(os.path.exists(updates_dir))

    def number_of_data_updates_applied(self):
        return get_resource_service("data_updates").find({}).count()

    def test_dry_data_update(self):
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = """
            count = mongodb_collection.find({}).count()
            assert count == 0, count
        """
        self.assertEqual(self.number_of_data_updates_applied(), 0)
        GenerateUpdate().run(resource_name="data_updates")
        Upgrade().run(dry=True)
        self.assertEqual(self.number_of_data_updates_applied(), 0)

    def test_fake_data_update(self):
        self.assertEqual(self.number_of_data_updates_applied(), 0)
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = "raise Exception()"
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = "raise Exception()"
        GenerateUpdate().run(resource_name="data_updates")
        self.assertEqual(self.number_of_data_updates_applied(), 0)
        Upgrade().run(fake=True)
        self.assertEqual(self.number_of_data_updates_applied(), 1)
        Downgrade().run(fake=True)
        self.assertEqual(self.number_of_data_updates_applied(), 0)

    def test_data_update(self):
        # create migrations
        for index in range(40):
            superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = """
            assert mongodb_collection
            count = mongodb_collection.find({}).count()
            assert count == %d, count
            assert mongodb_database
            """ % (
                index
            )
            superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = """
            assert mongodb_collection
            count = mongodb_collection.find({}).count()
            assert count == %d, count
            assert mongodb_database
            """ % (
                index + 1
            )
            GenerateUpdate().run(resource_name="data_updates")
        assert self.number_of_data_updates_applied() == 0
        thirdieth_update = get_data_updates_files(True)[29]
        Upgrade().run(data_update_id=thirdieth_update)
        assert self.number_of_data_updates_applied() == 30
        Upgrade().run()
        assert self.number_of_data_updates_applied() == 40
        Downgrade().run()
        assert self.number_of_data_updates_applied() == 39
        Downgrade().run(data_update_id=thirdieth_update)
        assert self.number_of_data_updates_applied() == 29
        Upgrade().run()

    def test_multiple_dirs(self):
        with mock.patch.dict(self.app.config, {"APPS_DATA_UPDATES_PATHS": ["/tmp/foo", "tmp/bar"]}):
            dirs = get_dirs()
            self.assertEqual(4, len(dirs))
