import os
import shutil
from unittest import mock

import superdesk.commands.data_updates
from superdesk import get_resource_service
from superdesk.commands.data_updates import (
    get_data_updates_files, GenerateUpdate, Upgrade, Downgrade
)
from superdesk.tests import TestCase

# change the folder where to store updates for test purpose
DEFAULT_DATA_UPDATE_DIR_NAME = '/tmp/data_updates'
MAIN_DATA_UPDATES_DIR = '/tmp/global_data_updates'


class DataUpdatesTestCase(TestCase):

    def setUp(self):

        dirs = (
            ('DEFAULT_DATA_UPDATE_DIR_NAME', '/tmp/data_updates'),
            ('MAIN_DATA_UPDATES_DIR', '/tmp/global_data_updates'),
        )
        for name, path in dirs:
            # if folder exists, removes
            shutil.rmtree(path, True)
            # create new folder for tests
            os.mkdir(path)

            def rm(path=path):
                shutil.rmtree(path)
            self.addCleanup(rm)

            patcher = mock.patch.object(superdesk.commands.data_updates, name, path)
            self.addCleanup(patcher.stop)
            patcher.start()

        # update the default implementation for `forwards` and `backwards` function
        dirs = (
            ('DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION', 'fw'),
            ('DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION', 'bw'),
        )
        for m, p in dirs:
            patcher = mock.patch('superdesk.commands.data_updates.%s' % m, 'pass')
            self.addCleanup(patcher.stop)
            patcher.start()

    def test_data_update_generation(self):
        assert len(get_data_updates_files()) is 0, get_data_updates_files()
        GenerateUpdate().run(resource_name='RESOURCE_NAME')
        assert len(get_data_updates_files()) is 1, get_data_updates_files()
        GenerateUpdate().run(resource_name='RESOURNCE_NAME')
        assert len(get_data_updates_files()) is 2, get_data_updates_files()

    def test_data_update_generation_create_updates_dir(self):
        updates_dir = DEFAULT_DATA_UPDATE_DIR_NAME
        shutil.rmtree(DEFAULT_DATA_UPDATE_DIR_NAME)
        self.assertFalse(os.path.exists(updates_dir))
        self.app.config['DATA_UPDATES_PATH'] = updates_dir
        GenerateUpdate().run('tmp')
        self.assertTrue(os.path.exists(updates_dir))

    def number_of_data_updates_applied(self):
        return get_resource_service('data_updates').find({}).count()

    def test_dry_data_update(self):
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = '''
            count = mongodb_collection.find({}).count()
            assert count is 0, count
        '''
        self.assertEqual(self.number_of_data_updates_applied(), 0)
        GenerateUpdate().run(resource_name='data_updates')
        Upgrade().run(dry=True)
        self.assertEqual(self.number_of_data_updates_applied(), 0)

    def test_fake_data_update(self):
        self.assertEqual(self.number_of_data_updates_applied(), 0)
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = 'raise Exception()'
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = 'raise Exception()'
        GenerateUpdate().run(resource_name='data_updates')
        self.assertEqual(self.number_of_data_updates_applied(), 0)
        Upgrade().run(fake=True)
        self.assertEqual(self.number_of_data_updates_applied(), 1)
        Downgrade().run(fake=True)
        self.assertEqual(self.number_of_data_updates_applied(), 0)

    def test_data_update(self):
        # create migrations
        for index in range(40):
            superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = '''
            assert(mongodb_collection)
            count = mongodb_collection.find({}).count()
            assert count is %d, count
            assert(mongodb_database)
            ''' % (index)
            superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = '''
            assert(mongodb_collection)
            count = mongodb_collection.find({}).count()
            assert count is %d, count
            assert(mongodb_database)
            ''' % (index + 1)
            GenerateUpdate().run(resource_name='data_updates')
        assert(self.number_of_data_updates_applied() is 0)
        thirdieth_update = get_data_updates_files(True)[29]
        Upgrade().run(data_update_id=thirdieth_update)
        assert(self.number_of_data_updates_applied() is 30)
        Upgrade().run()
        assert(self.number_of_data_updates_applied() is 40)
        Downgrade().run()
        assert(self.number_of_data_updates_applied() is 39)
        Downgrade().run(data_update_id=thirdieth_update)
        assert(self.number_of_data_updates_applied() is 29)
        Upgrade().run()
