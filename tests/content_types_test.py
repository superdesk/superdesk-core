
import unittest

from unittest.mock import patch
from apps.content_types import apply_schema


class MockService():

    def find_one(self, req, **lookup):
        return {
            'schema': {
                'headline': {}
            }
        }


class ContentTypesTestCase(unittest.TestCase):

    def test_apply_schema_default(self):
        item = {'guid': 'guid', 'headline': 'foo'}
        self.assertEqual(item, apply_schema(item))

    @patch('apps.content_types.content_types.get_resource_service', return_value=MockService())
    def test_apply_schema_profile(self, mock):
        item = {'headline': 'foo', 'slugline': 'bar', 'guid': '1', 'profile': 'test'}
        self.assertEqual({'headline': 'foo', 'guid': '1', 'profile': 'test'}, apply_schema(item))
