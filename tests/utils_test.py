import unittest
import superdesk.utils as utils


class UtilsTestCase(unittest.TestCase):
    def test_sha(self):
        digest = utils.sha("some text")
        self.assertGreater(len(digest), 40)

    def test_get_random_token(self):
        token = utils.get_random_token()
        self.assertGreater(len(token), 20)
        self.assertNotEqual(token, utils.get_random_token())

    def test_save_error_data(self):
        filename = utils.save_error_data("foo")
        self.assertIn("superdesk", filename)
        with open(filename) as f:
            self.assertEqual("foo", f.read())

    def test_timer(self):
        timer = utils.Timer()

        timer.start("test")
        self.assertIsNotNone(timer.split("test"))
        self.assertIsNotNone(timer.split("test"))
        self.assertIsNotNone(timer.stop("test"))
        self.assertRaises(KeyError, timer.split, "test")
        self.assertRaises(KeyError, timer.split, "bla")
