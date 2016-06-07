from superdesk.tests import TestCase
import superdesk.commands.data_updates
import superdesk
from superdesk.commands.data_updates import get_data_updates_files, GenerateUpdate, Upgrade, Downgrade
import shutil
import os

# change the folder where to store updates for test purpose
DATA_UPDATES_DIR = '/tmp/data_updates'


class DataUpdatesTestCase(TestCase):

    def setUp(self):
        super().setUp()
        # if folder exists, removes
        if os.path.exists(DATA_UPDATES_DIR):
            shutil.rmtree(DATA_UPDATES_DIR)
        # create new folder for tests
        os.mkdir(DATA_UPDATES_DIR)
        # update the folder in data_updates module
        superdesk.commands.data_updates.DATA_UPDATES_DIR = DATA_UPDATES_DIR
        # update the default implementation for `forwards` and `backwards` function
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = 'pass'
        superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = 'pass'

    def test_data_update_generation(self):
        assert(len(get_data_updates_files()) is 0)
        GenerateUpdate().run(resource_name='RESOURCE_NAME')
        assert(len(get_data_updates_files()) is 1)
        GenerateUpdate().run(resource_name='RESOURNCE_NAME')
        assert(len(get_data_updates_files()) is 2)

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
        for index in range(10):
            superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = '''
            assert(mongodb_collection)
            assert(mongodb_collection.find({}).count() is %d)
            assert(mongodb_database)
            ''' % (index)
            superdesk.commands.data_updates.DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = '''
            assert(mongodb_collection)
            assert(mongodb_collection.find({}).count() is %d)
            assert(mongodb_database)
            ''' % (index + 1)
            GenerateUpdate().run(resource_name='data_updates')
        assert(self.number_of_data_updates_applied() is 0)
        third_update = get_data_updates_files(True)[2]
        Upgrade().run(data_update_id=third_update)
        assert(self.number_of_data_updates_applied() is 3)
        Upgrade().run()
        assert(self.number_of_data_updates_applied() is 10)
        Downgrade().run()
        assert(self.number_of_data_updates_applied() is 9)
        Downgrade().run(data_update_id=third_update)
        assert(self.number_of_data_updates_applied() is 2)
