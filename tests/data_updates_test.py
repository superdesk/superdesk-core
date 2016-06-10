from superdesk.tests import TestCase
import superdesk.commands.data_updates
import superdesk
from superdesk.commands.data_updates import get_data_updates_files, GenerateUpdate, Upgrade, Downgrade
import shutil
import os

# change the folder where to store updates for test purpose
DEFAULT_DATA_UPDATE_DIR_NAME = '/tmp/data_updates'
MAIN_DATA_UPDATES_DIR = '/tmp/global_data_updates'


class DataUpdatesTestCase(TestCase):

    def setUp(self):
        super().setUp()
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

    def number_of_data_updates_applied(self):
        return superdesk.get_resource_service('data_updates').find({}).count()

    def test_fake_data_update(self):
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = 'raise Exception()'
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = 'raise Exception()'
        GenerateUpdate().run(resource_name='data_updates')
        Upgrade().run(fake=True)
        Downgrade().run(fake=True)

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
