import os
import shutil
import tempfile

from superdesk.tests import TestCase
import superdesk.commands.data_updates
import superdesk
from superdesk.commands.data_updates import get_data_updates_files, GenerateUpdate, Upgrade, Downgrade

# change the folder where to store updates for test purpose
DEFAULT_DATA_UPDATE_DIR_NAME = '/tmp/data_updates'
MAIN_DATA_UPDATES_DIR = '/tmp/global_data_updates'


class DataUpdatesTestCase(TestCase):

    def setUp(self):
        for folder in (DEFAULT_DATA_UPDATE_DIR_NAME, MAIN_DATA_UPDATES_DIR):
            # if folder exists, removes
            if os.path.exists(folder):
                shutil.rmtree(folder)
            # create new folder for tests
            os.mkdir(folder)
        # update the folder in data_updates module
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_DIR_NAME = DEFAULT_DATA_UPDATE_DIR_NAME
        superdesk.commands.data_updates.MAIN_DATA_UPDATES_DIR = MAIN_DATA_UPDATES_DIR
        # update the default implementation for `forwards` and `backwards` function
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = 'pass'
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = 'pass'

    def test_data_update_generation(self):
        assert len(get_data_updates_files()) is 0, get_data_updates_files()
        GenerateUpdate().run(resource_name='RESOURCE_NAME')
        assert len(get_data_updates_files()) is 1, get_data_updates_files()
        GenerateUpdate().run(resource_name='RESOURNCE_NAME')
        assert len(get_data_updates_files()) is 2, get_data_updates_files()

    def test_data_update_generation_create_updates_dir(self):
        updates_dir = tempfile.mkdtemp()
        shutil.rmtree(updates_dir)
        self.assertFalse(os.path.exists(updates_dir))
        self.app.config['DATA_UPDATES_PATH'] = updates_dir
        GenerateUpdate().run('tmp')
        print(updates_dir)
        self.assertTrue(os.path.exists(updates_dir))
        shutil.rmtree(updates_dir)

    def number_of_data_updates_applied(self):
        return superdesk.get_resource_service('data_updates').find({}).count()

    def test_dry_data_update(self):
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = '''
            count = mongodb_collection.find({}).count()
            assert count is 0, count
        '''
        assert(self.number_of_data_updates_applied() is 0)
        GenerateUpdate().run(resource_name='data_updates')
        Upgrade().run(dry=True)
        assert(self.number_of_data_updates_applied() is 0)

    def test_fake_data_update(self):
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = 'raise Exception()'
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = 'raise Exception()'
        GenerateUpdate().run(resource_name='data_updates')
        Upgrade().run(fake=True)
        assert(self.number_of_data_updates_applied() is 1)
        Downgrade().run(fake=True)
        assert(self.number_of_data_updates_applied() is 0)

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
