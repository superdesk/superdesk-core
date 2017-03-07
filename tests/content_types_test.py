from superdesk.tests import TestCase
from unittest import mock
import copy
from apps.content_types import content_types, apply_schema


class MockService():

    def find_one(self, req, **lookup):
        return {
            'schema': {
                'headline': {}
            }
        }


class ContentTypesTestCase(TestCase):

    def test_apply_schema_default(self):
        item = {'guid': 'guid', 'headline': 'foo'}
        self.assertEqual(item, apply_schema(item))

    @mock.patch('apps.content_types.content_types.get_resource_service', return_value=MockService())
    def test_apply_schema_profile(self, mock):
        item = {'headline': 'foo', 'slugline': 'bar', 'guid': '1', 'profile': 'test'}
        self.assertEqual({'headline': 'foo', 'guid': '1', 'profile': 'test'}, apply_schema(item))

    @mock.patch.object(content_types, 'get_fields_map_and_names', lambda: ({}, {}))
    def test_minlength(self):
        """Check that minlength is not modified when it is set

        check is done with required set
        """
        original = {
            "schema": {
                "body_html": {
                    "required": True,
                    "enabled": True
                },
            }}
        updates = copy.deepcopy(original)
        updates['schema']['body_html']['minlength'] = '99'
        content_types.ContentTypesService().on_update(updates, original)
        self.assertEqual(updates['schema']['body_html']['minlength'], '99')
