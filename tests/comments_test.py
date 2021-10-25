import unittest

from apps.comments.comments import encode_keys, decode_keys
from apps.comments.user_mentions import get_mentions


class CommentsTestCase(unittest.TestCase):
    def test_user_mentions(self):
        users, desks = get_mentions("hello @petr.jasek and #sports.desk and @a-_.")
        self.assertIn("a-_.", users)
        self.assertIn("petr.jasek", users)
        self.assertIn("sports.desk", desks)

    def test_encode_decode_keys(self):
        doc = {"foo": {"x.y": 1}}
        encode_keys(doc, "foo")
        for key in doc["foo"]:
            self.assertNotIn(".", key)
        decode_keys(doc, "foo")
        self.assertIn("x.y", doc["foo"])
        self.assertEqual(1, doc["foo"]["x.y"])
