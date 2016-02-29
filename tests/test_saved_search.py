
import unittest

from apps.saved_searches.saved_searches import encode_filter, decode_filter


class SavedSearchesTestCase(unittest.TestCase):

    def test_encode_decode_filter(self):
        data = {'foo': 'bar'}
        encoded = encode_filter(data)
        self.assertEqual('{"foo": "bar"}', encoded)
        self.assertEqual('{"foo": "bar"}', encode_filter(encoded))
        decoded = decode_filter(encoded)
        self.assertEqual(data, decoded)
        self.assertEqual(data, decode_filter(decoded))
