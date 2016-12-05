
import unittest
import superdesk.utils as utils


class UtilsTestCase(unittest.TestCase):

    def test_sha(self):
        digest = utils.sha('some text')
        self.assertGreater(len(digest), 40)

    def test_get_random_token(self):
        token = utils.get_random_token()
        self.assertGreater(len(token), 20)
        self.assertNotEqual(token, utils.get_random_token())
