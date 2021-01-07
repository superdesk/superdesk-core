import unittest
from superdesk.filemeta import get_filemeta, set_filemeta


class FilemetaTestCase(unittest.TestCase):
    def test_get_set_filemeta(self):
        item = {}
        set_filemeta(item, {"foo": "bar"})
        self.assertEqual("bar", get_filemeta(item, "foo"))
        self.assertEqual({"foo": "bar"}, get_filemeta(item))

    def test_get_filemeta_obsolete(self):
        item = {"filemeta": {"x": 1}}
        self.assertEqual(1, get_filemeta(item, "x"))
