
import unittest
from superdesk.utils import sha


class UtilsTestCase(unittest.TestCase):

    def test_sha(self):
        digest = sha('some text')
        self.assertGreater(len(digest), 40)
