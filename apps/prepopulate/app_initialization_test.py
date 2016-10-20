import os

from .app_initialize import AppInitializeWithDataCommand
from .app_scaffold_data import AppScaffoldDataCommand
from apps.prepopulate.app_initialize import fillEnvironmentVariables
from superdesk import get_resource_service, app
from superdesk.tests import TestCase


class AppInitializeWithDataCommandTestCase(TestCase):
    def _run(self, *a, **kw):
        command = AppInitializeWithDataCommand()
        return command.run(*a, **kw)

    def test_app_initialization(self):
        result = self._run()
        self.assertEqual(result, 0)

    def test_app_initialization_multiple_loads(self):
        result = self._run()
        self.assertEqual(result, 0)
        result = self._run()
        self.assertEqual(result, 0)

    def data_scaffolding_test(self):
        result = self._run(['desks', 'stages'], sample_data=True)
        self.assertEqual(result, 0)

        docs = [{
            '_id': str(x),
            'type': 'text',
            'abstract': 'test abstract {}'.format(x),
            'headline': 'test headline {}'.format(x),
            'body_html': 'test long story body {}'.format(x),
            'state': 'published'
        } for x in range(0, 40)]
        get_resource_service('published').post(docs)

        stories_per_desk = 2
        existing_desks = 18
        command = AppScaffoldDataCommand()
        result = command.run(stories_per_desk)
        self.assertEqual(result, 0)

        cursor = get_resource_service('desks').get_from_mongo(None, {})
        self.assertEqual(cursor.count(), existing_desks)

        cursor = get_resource_service('archive').get_from_mongo(None, {})
        self.assertEqual(cursor.count(), existing_desks * stories_per_desk)

    def test_sample_data(self):
        result = self._run(sample_data=True)
        self.assertEqual(result, 0)

        cursor = get_resource_service('desks').get_from_mongo(None, {})
        self.assertEqual(cursor.count(), 18)

    def test_app_initialization_index_creation(self):
        result = self._run()
        self.assertEqual(result, 0)
        result = app.data.mongo.pymongo(resource='users').db['users'].index_information()
        self.assertTrue('username_1' in result)
        self.assertTrue('first_name_1_last_name_-1' in result)
        result = app.data.mongo.pymongo(resource='archive').db['archive'].index_information()
        self.assertTrue('groups.refs.residRef_1' in result)
        self.assertTrue(result['groups.refs.residRef_1']['sparse'])

    def test_app_initialization_set_env_variables(self):
        os.environ.update({'REUTERS_USERNAME': 'r_username', 'REUTERS_PASSWORD': 'r_password'})
        item = {'username': '#ENV_REUTERS_USERNAME#', 'password': '#ENV_REUTERS_PASSWORD#'}
        crt_item = fillEnvironmentVariables(item)
        self.assertTrue(crt_item['username'] == 'r_username')
        self.assertTrue(crt_item['password'] == 'r_password')
        os.environ.pop('REUTERS_USERNAME')
        os.environ.pop('REUTERS_PASSWORD')

    def test_app_initialization_notset_env_variables(self):
        os.environ.update({'REUTERS_PASSWORD': 'r_password'})
        item = {'username': '#ENV_REUTERS_USERNAME#', 'password': '#ENV_REUTERS_PASSWORD#'}
        crt_item = fillEnvironmentVariables(item)
        self.assertTrue(not crt_item)
        os.environ.pop('REUTERS_PASSWORD')
